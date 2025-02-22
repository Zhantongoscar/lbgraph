#include "C:/clib/mysql/include/mysql.h"
#include <iostream>
#include <string>
#include <vector>
#include <set>
#include <fstream>
#include <sstream>
#include "nlohmann/json.hpp"

using json = nlohmann::json;

class TypeConnAnalyzer {
private:
    MYSQL* conn;
    std::string typesTableName;
    json rules;

    // 从预定义规则中找到合适的连接
    bool checkRulesForType(const std::string& type, const std::vector<std::string>& terminals, std::set<std::pair<std::string, std::string>>& conn_list) {
        if (terminals.size() != 2) {
            std::cerr << "类型 " << type << " 的终端数不为2" << std::endl;
            return false;
        }
        // 其他规则检查...
        return true;
    }

    bool loadConfig(std::string& host, std::string& user, std::string& password, std::string& database) {
        std::ifstream configFile("config.json");
        if (!configFile.is_open()) {
            std::cerr << "无法打开配置文件" << std::endl;
            return false;
        }

        json config;
        configFile >> config;
        configFile.close();

        if (!config.contains("mysql")) {
            std::cerr << "配置文件中未找到MySQL配置" << std::endl;
            return false;
        }

        auto& mysql = config["mysql"];
        host = mysql["host"];
        user = mysql["user"];
        password = mysql["password"];
        database = mysql["database"];
        return true;
    }

public:
    TypeConnAnalyzer() : typesTableName("panel_types") {
        // 加载预定义的连接规则
        std::ifstream rulesFile("c2_rules_type_conn.json");
        if (!rulesFile.is_open()) {
            std::cerr << "无法打开c2_rules_type_conn.json文件" << std::endl;
            return;
        }
        rulesFile >> rules;
        rulesFile.close();

        std::cout << "开始初始化MySQL..." << std::endl;
        conn = mysql_init(NULL);
        if (conn == NULL) {
            std::cerr << "MySQL初始化失败" << std::endl;
            return;
        }
        std::cout << "MySQL初始化成功" << std::endl;

        std::string host, user, password, database;
        std::cout << "加载配置文件..." << std::endl;
        if (!loadConfig(host, user, password, database)) {
            std::cerr << "加载配置失败" << std::endl;
            return;
        }
        std::cout << "配置加载成功" << std::endl;
        std::cout << "正在连接到MySQL数据库: " << host << ", 数据库: " << database << std::endl;

        if (!mysql_real_connect(conn, host.c_str(), user.c_str(), password.c_str(), 
                             database.c_str(), 0, NULL, 0)) {
            std::cerr << "连接MySQL失败: " << mysql_error(conn) << std::endl;
            return;
        }
        std::cout << "成功连接到MySQL数据库" << std::endl;
    }

    ~TypeConnAnalyzer() {
        if (conn) {
            mysql_close(conn);
        }
    }

    bool processConnections() {
        std::cout << "开始处理连接..." << std::endl;
        std::string query = "SELECT type, terminal_list FROM " + typesTableName;
        
        if (mysql_query(conn, query.c_str())) {
            std::cerr << "查询失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        MYSQL_RES* result = mysql_store_result(conn);
        if (!result) {
            std::cerr << "获取结果失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        std::set<std::pair<std::string, std::string>> inner_conn_list;
        MYSQL_ROW row;
        while ((row = mysql_fetch_row(result))) {
            std::string type = row[0];
            json terminals = json::parse(row[1]);
            std::vector<std::string> terminal_vec = terminals.get<std::vector<std::string>>();
            
            if (!checkRulesForType(type, terminal_vec, inner_conn_list)) {
                std::cerr << "处理类型 " << type << " 失败" << std::endl;
                continue;
            }
            
            std::cout << "处理类型: " << type 
                      << ", 终端数: " << terminal_vec.size() 
                      << ", 原始JSON: " << row[1] << std::endl;
        }

        mysql_free_result(result);

        // 将结果保存到JSON文件
        json output;
        output["connections"] = json::array();
        for (const auto& conn : inner_conn_list) {
            json connection;
            connection["from"] = conn.first;
            connection["to"] = conn.second;
            if (conn.first == "A1" || conn.first == "A2") {
                connection["type"] = "coil_connection";
                connection["description"] = "线圈连接";
            } else {
                connection["type"] = "contact_connection";
                connection["description"] = "触点组" + std::string(1, conn.first[0]) + "连接";
            }
            output["connections"].push_back(connection);
        }

        std::ofstream outFile("inner_rules.json");
        if (!outFile.is_open()) {
            std::cerr << "无法创建inner_rules.json文件" << std::endl;
            return false;
        }
        outFile << output.dump(2);
        outFile.close();

        std::cout << "连接规则已保存到inner_rules.json" << std::endl;
        return true;
    }
};

int main() {
    TypeConnAnalyzer analyzer;
    if (!analyzer.processConnections()) {
        std::cerr << "处理连接失败" << std::endl;
        return 1;
    }
    return 0;
}