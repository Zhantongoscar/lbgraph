#include <iostream>
#include <fstream>
#include <string>
#include <sstream>
#include <regex>
#include "C:/clib/mysql/include/mysql.h"
#include "nlohmann/json.hpp"

using json = nlohmann::json;

class GraphConnCreator {
private:
    MYSQL* conn;
    std::string mysql_host;
    std::string mysql_user;
    std::string mysql_password;
    std::string mysql_database;
    std::string neo4j_uri;
    std::string neo4j_username;
    std::string neo4j_password;
    std::string csv_file;

    std::string convertHttpToBoltUri(const std::string& http_uri) {
        std::regex http_pattern("http://(.*?)(:\\d+)?(/.*)?");
        std::smatch matches;
        
        if (std::regex_match(http_uri, matches, http_pattern)) {
            std::string host = matches[1].str();
            std::string port = matches[2].str();
            
            if (port.empty()) {
                port = ":7687";
            } else if (port == ":7474") {
                port = ":7687";
            }
            
            return "bolt://" + host + port;
        }
        
        return "bolt://" + http_uri;
    }

    bool loadConfig() {
        try {
            std::ifstream configFile("config.json");
            if (!configFile.is_open()) {
                std::cerr << "无法打开config.json文件" << std::endl;
                return false;
            }

            json config;
            configFile >> config;

            mysql_host = config["mysql"]["host"];
            mysql_user = config["mysql"]["user"];
            mysql_password = config["mysql"]["password"];
            mysql_database = config["mysql"]["database"];

            neo4j_uri = config["neo4j"]["uri"];
            neo4j_username = config["neo4j"]["username"];
            neo4j_password = config["neo4j"]["password"];
            
            if (neo4j_uri.find("http://") == 0) {
                std::string bolt_uri = convertHttpToBoltUri(neo4j_uri);
                std::cout << "将Neo4j HTTP URI转换为Bolt URI: " << neo4j_uri << " -> " << bolt_uri << std::endl;
                neo4j_uri = bolt_uri;
            } else if (neo4j_uri.find("bolt://") != 0 && neo4j_uri.find("neo4j://") != 0) {
                neo4j_uri = "bolt://" + neo4j_uri;
                std::cout << "添加bolt://前缀到Neo4j URI: " << neo4j_uri << std::endl;
            }

            return true;
        }
        catch (const std::exception& e) {
            std::cerr << "读取配置文件失败: " << e.what() << std::endl;
            return false;
        }
    }

    bool connectToMysql() {
        conn = mysql_init(NULL);
        if (conn == NULL) {
            std::cerr << "MySQL初始化失败" << std::endl;
            return false;
        }

        if (!mysql_real_connect(conn, mysql_host.c_str(), mysql_user.c_str(), 
            mysql_password.c_str(), mysql_database.c_str(), 0, NULL, 0)) {
            std::cerr << "MySQL连接失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        mysql_set_character_set(conn, "utf8");
        return true;
    }

    bool exportConnectionsToCSV() {
        csv_file = "output/connections_export.csv";
        
        system("if not exist output mkdir output");
        
        std::ofstream csvOutput(csv_file);
        if (!csvOutput.is_open()) {
            std::cerr << "无法创建CSV文件: " << csv_file << std::endl;
            return false;
        }
        
        csvOutput << "source,target,connNo,connType,color,isCable,voltage,current,resistance" << std::endl;
        
        if (mysql_query(conn, "SELECT source, target, connNo, connType, color, isCable, voltage, current, resistance FROM conn_graph WHERE isInPanel=1")) {
            std::cerr << "查询conn_graph失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        MYSQL_RES* result = mysql_store_result(conn);
        if (result == NULL) {
            std::cerr << "获取结果集失败" << std::endl;
            return false;
        }

        int num_fields = mysql_num_fields(result);
        MYSQL_ROW row;
        int count = 0;
        
        while ((row = mysql_fetch_row(result))) {
            for (int i = 0; i < num_fields; i++) {
                if (i > 0) csvOutput << ",";
                if (row[i]) {
                    std::string value = row[i];
                    if (value.find(',') != std::string::npos || 
                        value.find('"') != std::string::npos) {
                        size_t pos = 0;
                        while ((pos = value.find('"', pos)) != std::string::npos) {
                            value.replace(pos, 1, "\"\"");
                            pos += 2;
                        }
                        csvOutput << "\"" << value << "\"";
                    } else {
                        csvOutput << value;
                    }
                } else {
                    csvOutput << "";
                }
            }
            csvOutput << std::endl;
            count++;
        }

        mysql_free_result(result);
        csvOutput.close();
        
        std::cout << "已导出 " << count << " 条连接记录到CSV文件: " << csv_file << std::endl;
        return true;
    }

    bool createConnectionsInNeo4j() {
        std::string pythonScript = "import_connections_to_neo4j.py";
        std::ofstream scriptFile(pythonScript);
        
        if (!scriptFile.is_open()) {
            std::cerr << "无法创建Python脚本文件" << std::endl;
            return false;
        }
        
        scriptFile << "import csv\n";
        scriptFile << "import sys\n";
        scriptFile << "from neo4j import GraphDatabase\n\n";
        
        scriptFile << "uri = '" << neo4j_uri << "'\n";
        scriptFile << "username = '" << neo4j_username << "'\n";
        scriptFile << "password = '" << neo4j_password << "'\n\n";
        
        scriptFile << "print(f'连接到Neo4j数据库: {uri}')\n";
        scriptFile << "try:\n";
        scriptFile << "    driver = GraphDatabase.driver(uri, auth=(username, password))\n";
        scriptFile << "    \n";
        scriptFile << "    with driver.session() as session:\n";
        scriptFile << "        result = session.run('RETURN 1 AS test')\n";
        scriptFile << "        test_value = result.single()['test']\n";
        scriptFile << "        print(f'连接测试成功: {test_value}')\n\n";
        
        scriptFile << "        # 检查节点数量\n";
        scriptFile << "        result = session.run('MATCH (d:V_Device) RETURN count(d) AS deviceCount')\n";
        scriptFile << "        device_count = result.single()['deviceCount']\n";
        scriptFile << "        print(f'数据库中存在 {device_count} 个V_Device节点')\n\n";
        
        scriptFile << "        result = session.run('MATCH (t:V_terminal) RETURN count(t) AS terminalCount')\n";
        scriptFile << "        terminal_count = result.single()['terminalCount']\n";
        scriptFile << "        print(f'数据库中存在 {terminal_count} 个V_Terminal节点')\n\n";
        
        scriptFile << "        # 清空现有连接关系\n";
        scriptFile << "        result = session.run('MATCH ()-[r:CONN]->() DELETE r')\n";
        scriptFile << "        print('已清除所有现有连接关系')\n\n";
        
        scriptFile << "    # 从CSV文件导入连接关系\n";
        scriptFile << "    conn_count = 0\n";
        scriptFile << "    fail_count = 0\n";
        scriptFile << "    with open('" << csv_file << "', 'r', encoding='utf-8') as file:\n";
        scriptFile << "        reader = csv.DictReader(file)\n";
        scriptFile << "        for row in reader:\n";
        scriptFile << "            with driver.session() as session:\n";
        scriptFile << "                cypher = '''\n";
        scriptFile << "                    MATCH (source)\n";
        scriptFile << "                    WHERE source.fdid = $source\n";
        scriptFile << "                    AND (source:V_Device OR source:V_terminal)\n";
        scriptFile << "                    MATCH (target)\n";
        scriptFile << "                    WHERE target.fdid = $target\n";
        scriptFile << "                    AND (target:V_Device OR target:V_terminal)\n";
        scriptFile << "                    CREATE (source)-[r:CONN {\n";
        scriptFile << "                        connNo: $connNo,\n";
        scriptFile << "                        type: $connType,\n";
        scriptFile << "                        color: $color,\n";
        scriptFile << "                        isCable: $isCable,\n";
        scriptFile << "                        voltage: $voltage,\n";
        scriptFile << "                        current: $current,\n";
        scriptFile << "                        resistance: $resistance\n";
        scriptFile << "                    }]->(target)\n";
        scriptFile << "                    RETURN r\n";
        scriptFile << "                '''\n";
        scriptFile << "                try:\n";
        scriptFile << "                    result = session.run(\n";
        scriptFile << "                        cypher,\n";
        scriptFile << "                        source=row['source'],\n";
        scriptFile << "                        target=row['target'],\n";
        scriptFile << "                        connNo=row['connNo'],\n";
        scriptFile << "                        connType=row['connType'],\n";
        scriptFile << "                        color=row['color'],\n";
        scriptFile << "                        isCable=row['isCable'] == '1',\n";
        scriptFile << "                        voltage=float(row['voltage'] or 0),\n";
        scriptFile << "                        current=float(row['current'] or 0),\n";
        scriptFile << "                        resistance=float(row['resistance'] or 0)\n";
        scriptFile << "                    )\n";
        scriptFile << "                    if not result.peek():\n";
        scriptFile << "                        print('未能找到节点: source=' + row['source'] + ', target=' + row['target'])\n";
        scriptFile << "                        fail_count += 1\n";
        scriptFile << "                    else:\n";
        scriptFile << "                        conn_count += 1\n";
        scriptFile << "                        if conn_count % 100 == 0:\n";
        scriptFile << "                            print(f'已创建 {conn_count} 个连接关系')\n";
        scriptFile << "                except Exception as e:\n";
        scriptFile << "                    print(f'创建连接失败: {e}', file=sys.stderr)\n";
        scriptFile << "                    fail_count += 1\n\n";
        
        scriptFile << "    print(f'总共创建了 {conn_count} 个连接关系，失败 {fail_count} 个')\n\n";
        scriptFile << "    # 验证连接关系数量\n";
        scriptFile << "    with driver.session() as session:\n";
        scriptFile << "        result = session.run('MATCH ()-[r:CONN]->() RETURN count(r) AS connCount')\n";
        scriptFile << "        conn_count = result.single()['connCount']\n";
        scriptFile << "        print(f'数据库中实际存在 {conn_count} 个CONN关系')\n\n";
        
        scriptFile << "    driver.close()\n";
        scriptFile << "except Exception as e:\n";
        scriptFile << "    print(f'错误: {e}', file=sys.stderr)\n";
        scriptFile << "    sys.exit(1)\n";
        
        scriptFile.close();
        
        std::cout << "执行Python脚本导入数据到Neo4j..." << std::endl;
        int result = system("python --version > nul 2>&1");
        
        if (result != 0) {
            std::cerr << "未找到Python命令，尝试使用python3命令..." << std::endl;
            result = system("python3 --version > nul 2>&1");
            
            if (result != 0) {
                std::cerr << "未找到Python3命令，请确保Python已安装并添加到PATH环境变量中" << std::endl;
                return false;
            }
            
            result = system("python3 -m pip install neo4j > nul 2>&1");
            if (result != 0) {
                std::cerr << "无法安装Neo4j Python驱动，请手动运行: pip install neo4j" << std::endl;
            }
            
            result = system(("python3 " + pythonScript).c_str());
        } else {
            result = system("python -m pip install neo4j > nul 2>&1");
            if (result != 0) {
                std::cerr << "无法安装Neo4j Python驱动，请手动运行: pip install neo4j" << std::endl;
            }
            
            result = system(("python " + pythonScript).c_str());
        }
        
        if (result != 0) {
            std::cerr << "执行Python脚本失败，错误代码: " << result << std::endl;
            std::cerr << "请确保已安装Neo4j Python驱动: pip install neo4j" << std::endl;
            return false;
        }
        
        return true;
    }

    bool createGraphFromConnections() {
        if (!exportConnectionsToCSV()) {
            return false;
        }
        
        if (!createConnectionsInNeo4j()) {
            return false;
        }
        
        return true;
    }

public:
    GraphConnCreator() : conn(nullptr) {}
    
    ~GraphConnCreator() {
        if (conn) {
            mysql_close(conn);
        }
    }

    bool run() {
        if (!loadConfig()) {
            return false;
        }

        if (!connectToMysql()) {
            return false;
        }

        bool success = createGraphFromConnections();

        return success;
    }
};

int main() {
    GraphConnCreator creator;
    if (!creator.run()) {
        std::cerr << "程序执行失败" << std::endl;
        return 1;
    }
    
    std::cout << "成功创建连接关系" << std::endl;
    return 0;
}