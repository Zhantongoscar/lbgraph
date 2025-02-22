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
    json rules;

    bool checkRulesForDevice(const std::string& deviceId, const std::vector<std::string>& terminals, std::set<std::pair<std::string, std::string>>& conn_list) {
        if (terminals.empty()) {
            std::cerr << "设备 " << deviceId << " 没有终端" << std::endl;
            return false;
        }

        // 遍历规则，只添加规则中定义的连接
        for (const auto& rule : rules["rules"]) {
            std::string term1 = rule[0];
            std::string term2 = rule[1];
            
            // 检查这个设备是否有规则中的两个端子
            bool hasFirst = std::find(terminals.begin(), terminals.end(), term1) != terminals.end();
            bool hasSecond = std::find(terminals.begin(), terminals.end(), term2) != terminals.end();
            
            // 如果设备有这两个端子，添加连接
            if (hasFirst && hasSecond) {
                conn_list.insert(std::make_pair(term1, term2));
                std::cout << "设备 " << deviceId << " 添加连接: " << term1 << " -> " << term2 << std::endl;
            }
        }
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
    TypeConnAnalyzer() {
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
        
        // 设置 MySQL 连接的字符集为 UTF-8
        if (mysql_set_character_set(conn, "utf8mb4")) {
            std::cerr << "设置字符集失败: " << mysql_error(conn) << std::endl;
            return;
        }
        std::cout << "成功连接到MySQL数据库，字符集设置为 utf8mb4" << std::endl;
    }

    ~TypeConnAnalyzer() {
        if (conn) {
            mysql_close(conn);
        }
    }

    bool processConnections() {
        // 设置 MySQL 连接的字符集为 UTF-8
        mysql_set_character_set(conn, "utf8mb4");
        
        std::cout << "开始处理连接..." << std::endl;
        std::string query = "SELECT id, terminal_list FROM panel_device_inner";
        
        if (mysql_query(conn, query.c_str())) {
            std::cerr << "查询失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        MYSQL_RES* result = mysql_store_result(conn);
        if (!result) {
            std::cerr << "获取结果失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        MYSQL_ROW row;
        while ((row = mysql_fetch_row(result))) {
            std::string id = row[0];
            json terminals = json::parse(row[1]);
            std::vector<std::string> terminal_vec = terminals.get<std::vector<std::string>>();
            
            std::set<std::pair<std::string, std::string>> inner_conn_list;
            if (!checkRulesForDevice(id, terminal_vec, inner_conn_list)) {
                std::cerr << "处理设备 " << id << " 失败" << std::endl;
                continue;
            }
            
            // 将连接信息转换为JSON格式
            json connections = json::array();
            for (const auto& conn : inner_conn_list) {
                json connection;
                connection["from"] = conn.first;
                connection["to"] = conn.second;
                if (conn.first == "A1" || conn.first == "A2" || conn.second == "A1" || conn.second == "A2") {
                    connection["type"] = "coil_connection";
                    connection["description"] = u8"线圈连接";
                } else {
                    std::string groupName;
                    if (isdigit(conn.first[0])) {
                        groupName = std::string(1, conn.first[0]);
                    } else if (isdigit(conn.second[0])) {
                        groupName = std::string(1, conn.second[0]);
                    } else {
                        groupName = conn.first[0] == 'L' ? "L" : "T";
                    }
                    connection["type"] = "contact_connection";
                    connection["description"] = u8"触点组" + groupName + u8"连接";
                }
                connections.push_back(connection);
            }

            // 更新数据库中的inner_conn_list字段
            std::string updateQuery = "UPDATE panel_device_inner SET inner_conn_list = ? WHERE id = ?";
            
            MYSQL_STMT* stmt = mysql_stmt_init(conn);
            if (!stmt) {
                std::cerr << "mysql_stmt_init() failed" << std::endl;
                continue;
            }

            if (mysql_stmt_prepare(stmt, updateQuery.c_str(), updateQuery.length())) {
                std::cerr << "mysql_stmt_prepare() failed: " << mysql_stmt_error(stmt) << std::endl;
                mysql_stmt_close(stmt);
                continue;
            }

            std::string connectionsJson = connections.dump();
            
            MYSQL_BIND bind[2];
            memset(bind, 0, sizeof(bind));
            
            bind[0].buffer_type = MYSQL_TYPE_STRING;
            bind[0].buffer = (void*)connectionsJson.c_str();
            bind[0].buffer_length = connectionsJson.length();
            
            bind[1].buffer_type = MYSQL_TYPE_STRING;
            bind[1].buffer = (void*)id.c_str();
            bind[1].buffer_length = id.length();

            if (mysql_stmt_bind_param(stmt, bind)) {
                std::cerr << "mysql_stmt_bind_param() failed: " << mysql_stmt_error(stmt) << std::endl;
                mysql_stmt_close(stmt);
                continue;
            }

            if (mysql_stmt_execute(stmt)) {
                std::cerr << "mysql_stmt_execute() failed: " << mysql_stmt_error(stmt) << std::endl;
            } else {
                std::cout << "已更新设备 " << id << " 的连接信息" << std::endl;
            }

            mysql_stmt_close(stmt);
        }

        mysql_free_result(result);
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