#include <iostream>
#include <fstream>
#include <string>
#include <sstream>
#include <regex>
#include "C:/clib/mysql/include/mysql.h"
#include "nlohmann/json.hpp"

using json = nlohmann::json;

class GraphDeviceCreator {
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

    // 转换HTTP URI为Bolt URI
    std::string convertHttpToBoltUri(const std::string& http_uri) {
        std::regex http_pattern("http://(.*?)(:\\d+)?(/.*)?");
        std::smatch matches;
        
        if (std::regex_match(http_uri, matches, http_pattern)) {
            std::string host = matches[1].str();
            std::string port = matches[2].str();
            
            // 如果没有指定端口，默认使用7687（Neo4j Bolt默认端口）
            if (port.empty()) {
                port = ":7687";
            } else if (port == ":7474") {
                // 如果是HTTP默认端口7474，转换为Bolt默认端口7687
                port = ":7687";
            }
            
            return "bolt://" + host + port;
        }
        
        // 如果无法解析，返回原始URI加上bolt://前缀
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

            // 读取MySQL配置
            mysql_host = config["mysql"]["host"];
            mysql_user = config["mysql"]["user"];
            mysql_password = config["mysql"]["password"];
            mysql_database = config["mysql"]["database"];

            // 读取Neo4j配置
            neo4j_uri = config["neo4j"]["uri"];
            neo4j_username = config["neo4j"]["username"];
            neo4j_password = config["neo4j"]["password"];
            
            // 转换HTTP URI为Bolt URI
            if (neo4j_uri.find("http://") == 0) {
                std::string bolt_uri = convertHttpToBoltUri(neo4j_uri);
                std::cout << "将Neo4j HTTP URI转换为Bolt URI: " << neo4j_uri << " -> " << bolt_uri << std::endl;
                neo4j_uri = bolt_uri;
            } else if (neo4j_uri.find("bolt://") != 0 && neo4j_uri.find("neo4j://") != 0) {
                // 如果不是以bolt://或neo4j://开头，假设它是主机名，添加bolt://前缀
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

        // 设置字符集为UTF8
        mysql_set_character_set(conn, "utf8");
        return true;
    }

    // 导出MySQL设备数据为CSV文件，只选择isInPanel=1的设备
    bool exportDevicesToCSV() {
        csv_file = "output/devices_export.csv";
        
        // 确保目录存在
        system("if not exist output mkdir output");
        
        std::ofstream csvOutput(csv_file);
        if (!csvOutput.is_open()) {
            std::cerr << "无法创建CSV文件: " << csv_file << std::endl;
            return false;
        }
        
        // 写入CSV标题行，包含Type、isSim、isPLC和isTerminal字段
        csvOutput << "id,fdid,function,location,device,Type,isSim,isPLC,isTerminal" << std::endl;
        
        // 修改查询语句，添加条件只选择isInPanel=1的设备，确保输出Type、isSim、isPLC和isTerminal字段
        if (mysql_query(conn, "SELECT id,fdid,function,location,device,Type,isSim,isPLC,isTerminal FROM v_devices WHERE isInPanel=1")) {
            std::cerr << "查询v_devices失败: " << mysql_error(conn) << std::endl;
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
                    // 转义CSV中的逗号和引号
                    if (value.find(',') != std::string::npos || 
                        value.find('"') != std::string::npos) {
                        // 替换所有引号为双引号
                        size_t pos = 0;
                        while ((pos = value.find('"', pos)) != std::string::npos) {
                            value.replace(pos, 1, "\"\"");
                            pos += 2;
                        }
                        // 在值的两边加上引号
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
        
        std::cout << "已导出 " << count << " 条设备记录到CSV文件: " << csv_file << std::endl;
        return true;
    }

    bool createDeviceNodesInNeo4j() {
        // 创建Python脚本执行Neo4j导入
        std::string pythonScript = "import_devices_to_neo4j.py";
        std::ofstream scriptFile(pythonScript);
        
        if (!scriptFile.is_open()) {
            std::cerr << "无法创建Python脚本文件" << std::endl;
            return false;
        }
        
        // 写入Python脚本内容
        scriptFile << "import csv\n";
        scriptFile << "import sys\n";
        scriptFile << "from neo4j import GraphDatabase\n\n";
        
        scriptFile << "# Neo4j连接信息\n";
        scriptFile << "uri = '" << neo4j_uri << "'\n";
        scriptFile << "username = '" << neo4j_username << "'\n";
        scriptFile << "password = '" << neo4j_password << "'\n\n";
        
        scriptFile << "print(f'连接到Neo4j数据库: {uri}')\n";
        scriptFile << "try:\n";
        scriptFile << "    # 连接到Neo4j数据库\n";
        scriptFile << "    driver = GraphDatabase.driver(uri, auth=(username, password))\n";
        scriptFile << "    \n";
        scriptFile << "    # 测试连接\n";
        scriptFile << "    with driver.session() as session:\n";
        scriptFile << "        result = session.run('RETURN 1 AS test')\n";
        scriptFile << "        test_value = result.single()['test']\n";
        scriptFile << "        print(f'连接测试成功: {test_value}')\n\n";
        
        scriptFile << "    # 清空现有设备节点\n";
        scriptFile << "    with driver.session() as session:\n";
        scriptFile << "        result = session.run('MATCH (d:V_Device) DELETE d')\n";
        scriptFile << "        print('已清除所有现有设备节点')\n\n";
        
        scriptFile << "    # 从CSV文件导入设备节点\n";
        scriptFile << "    device_count = 0\n";
        scriptFile << "    with open('" << csv_file << "', 'r', encoding='utf-8') as file:\n";
        scriptFile << "        reader = csv.DictReader(file)\n";
        scriptFile << "        for row in reader:\n";
        scriptFile << "            with driver.session() as session:\n";
        scriptFile << "                session.run(\n";
        scriptFile << "                    'CREATE (d:V_Device {id: $id, fdid: $fdid, function: $function, location: $location, device: $device, Type: $Type, isSim: $isSim, isPLC: $isPLC, isTerminal: $isTerminal})',\n";
        scriptFile << "                    id=row['id'],\n";
        scriptFile << "                    fdid=row['fdid'],\n";
        scriptFile << "                    function=row['function'],\n";
        scriptFile << "                    location=row['location'],\n";
        scriptFile << "                    device=row['device'],\n";
        scriptFile << "                    Type=row['Type'],\n";
        scriptFile << "                    isSim=row['isSim'],\n";
        scriptFile << "                    isPLC=row['isPLC'],\n";
        scriptFile << "                    isTerminal=row['isTerminal']\n";
        scriptFile << "                )\n";
        scriptFile << "            device_count += 1\n";
        scriptFile << "            if device_count % 100 == 0:\n";
        scriptFile << "                print(f'已创建 {device_count} 个设备节点')\n\n";
        
        scriptFile << "    print(f'总共创建了 {device_count} 个设备节点')\n";
        scriptFile << "    driver.close()\n";
        scriptFile << "except Exception as e:\n";
        scriptFile << "    print(f'错误: {e}', file=sys.stderr)\n";
        scriptFile << "    sys.exit(1)\n";
        
        scriptFile.close();
        
        // 检查python命令是否可用
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

    bool createGraphFromDevices() {
        if (!exportDevicesToCSV()) {
            return false;
        }
        
        if (!createDeviceNodesInNeo4j()) {
            return false;
        }
        
        return true;
    }

public:
    GraphDeviceCreator() : conn(nullptr) {}
    
    ~GraphDeviceCreator() {
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

        bool success = createGraphFromDevices();

        return success;
    }
};

int main() {
    GraphDeviceCreator creator;
    if (!creator.run()) {
        std::cerr << "程序执行失败" << std::endl;
        return 1;
    }
    
    std::cout << "成功创建设备图" << std::endl;
    return 0;
}