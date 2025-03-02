#include <iostream>
#include <fstream>
#include <string>
#include <regex>
#include "C:/clib/mysql/include/mysql.h"
#include "nlohmann/json.hpp"

using json = nlohmann::json;

std::string generate_python_script(const std::string& uri, const std::string& username, const std::string& password, const std::string& csv_file) {
    return "import csv\n"
           "import sys\n"
           "from neo4j import GraphDatabase\n\n"
           "uri = '" + uri + "'\n"
           "username = '" + username + "'\n"
           "password = '" + password + "'\n\n"
           "try:\n"
           "    driver = GraphDatabase.driver(uri, auth=(username, password))\n"
           "    with driver.session() as session:\n"
           "        result = session.run('RETURN 1 AS test')\n"
           "        test_value = result.single()['test']\n"
           "        print(f'连接测试成功: {test_value}')\n\n"
           "        session.run('MATCH (t:V_Terminal) DELETE t')\n"
           "        print('已清除所有现有终端节点')\n\n"
           "    terminal_count = 0\n"
           "    with open('" + csv_file + "', 'r', encoding='utf-8') as file:\n"
           "        reader = csv.DictReader(file)\n"
           "        for row in reader:\n"
           "            with driver.session() as session:\n"
           "                session.run('CREATE (t:V_Terminal $props)', props=row)\n"
           "            terminal_count += 1\n"
           "            if terminal_count % 100 == 0:\n"
           "                print(f'已创建 {terminal_count} 个终端节点')\n"
           "    with driver.session() as session:\n"
           "        session.run('MATCH (d:V_Device), (t:V_Terminal) WHERE d.id = t.device_id CREATE (d)-[:HAS_TERMINAL]->(t)')\n"
           "        print('已创建设备和终端之间的关系')\n"
           "        result = session.run('\n"
           "            MATCH (t:V_Terminal)\n"
           "            WITH DISTINCT SPLIT(t.FTID, \"+\")[0] as prefix\n"
           "            RETURN prefix, count(*) as count\n"
           "            ORDER BY count DESC\n"
           "        ')\n"
           "        print('\\n节点统计:')\n"
           "        for record in result:\n"
           "            print(f\"  {record['prefix']}: {record['count']}个节点\")\n"
           "    driver.close()\n"
           "except Exception as e:\n"
           "    print(f'错误: {e}', file=sys.stderr)\n"
           "    sys.exit(1)\n";
}

class GraphTerminalCreator {
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
                std::regex http_pattern("http://(.*?)(:\\d+)?(/.*)?");
                std::smatch matches;
                if (std::regex_match(neo4j_uri, matches, http_pattern)) {
                    std::string host = matches[1].str();
                    std::string port = matches[2].str().empty() ? ":7687" : ":7687";
                    neo4j_uri = "bolt://" + host + port;
                }
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
        if (!conn || !mysql_real_connect(conn, mysql_host.c_str(), mysql_user.c_str(), 
            mysql_password.c_str(), mysql_database.c_str(), 0, NULL, 0)) {
            std::cerr << "MySQL连接失败: " << mysql_error(conn) << std::endl;
            return false;
        }
        mysql_set_character_set(conn, "utf8");
        return true;
    }

    bool exportTerminalsToCSV() {
        csv_file = "output/terminals_export.csv";
        system("if not exist output mkdir output");
        
        std::ofstream csvOutput(csv_file);
        if (!csvOutput.is_open()) {
            std::cerr << "无法创建CSV文件" << std::endl;
            return false;
        }

        const char* query = "SELECT * FROM v_device_points WHERE Location LIKE 'K1.%' OR Location LIKE 'S1%'";
        if (mysql_query(conn, query)) {
            std::cerr << "查询失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        MYSQL_RES* result = mysql_store_result(conn);
        if (!result) {
            std::cerr << "获取结果集失败" << std::endl;
            return false;
        }

        MYSQL_FIELD* fields = mysql_fetch_fields(result);
        int num_fields = mysql_num_fields(result);
        
        // 写入标题行
        for (int i = 0; i < num_fields; i++) {
            if (i > 0) csvOutput << ",";
            csvOutput << fields[i].name;
        }
        csvOutput << std::endl;

        // 写入数据行
        MYSQL_ROW row;
        int count = 0;
        while ((row = mysql_fetch_row(result))) {
            for (int i = 0; i < num_fields; i++) {
                if (i > 0) csvOutput << ",";
                if (row[i]) {
                    std::string value = row[i];
                    if (value.find(',') != std::string::npos || value.find('"') != std::string::npos) {
                        csvOutput << "\"" << value << "\"";
                    } else {
                        csvOutput << value;
                    }
                }
            }
            csvOutput << std::endl;
            count++;
        }

        mysql_free_result(result);
        csvOutput.close();
        std::cout << "已导出 " << count << " 条记录到 " << csv_file << std::endl;
        return true;
    }

    bool createTerminalNodesInNeo4j() {
        std::string pythonScript = "import_terminals_to_neo4j.py";
        std::ofstream scriptFile(pythonScript);
        if (!scriptFile.is_open()) {
            std::cerr << "无法创建Python脚本" << std::endl;
            return false;
        }

        scriptFile << generate_python_script(neo4j_uri, neo4j_username, neo4j_password, csv_file);
        scriptFile.close();

        std::string cmd = "python " + pythonScript;
        int result = system(cmd.c_str());
        return result == 0;
    }

public:
    GraphTerminalCreator() : conn(nullptr) {}
    
    ~GraphTerminalCreator() {
        if (conn) mysql_close(conn);
    }

    bool run() {
        return loadConfig() && 
               connectToMysql() && 
               exportTerminalsToCSV() && 
               createTerminalNodesInNeo4j();
    }
};

int main() {
    GraphTerminalCreator creator;
    if (!creator.run()) {
        std::cerr << "程序执行失败" << std::endl;
        return 1;
    }
    std::cout << "成功创建终端图" << std::endl;
    return 0;
}