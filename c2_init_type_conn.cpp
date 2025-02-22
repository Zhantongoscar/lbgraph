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

    bool validateRules(const json& rulesJson) {
        if (!rulesJson.contains("rules")) {
            std::cerr << "错误：JSON文件缺少'rules'字段" << std::endl;
            return false;
        }

        if (!rulesJson["rules"].is_array()) {
            std::cerr << "错误：'rules'字段不是数组" << std::endl;
            return false;
        }

        for (const auto& rule : rulesJson["rules"]) {
            if (!rule.is_array() || rule.size() != 2) {
                std::cerr << "错误：规则格式错误，每个规则必须是包含两个元素的数组" << std::endl;
                return false;
            }
            if (!rule[0].is_string() || !rule[1].is_string()) {
                std::cerr << "错误：规则中的端子必须是字符串" << std::endl;
                return false;
            }
        }

        std::cout << "规则验证通过，共 " << rulesJson["rules"].size() << " 条规则" << std::endl;
        return true;
    }

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

    bool loadRules() {
        try {
            std::cout << "开始加载连接规则文件..." << std::endl;
            std::ifstream rulesFile("c2_rules_type_conn.json");
            if (!rulesFile.is_open()) {
                std::cerr << "错误：无法打开c2_rules_type_conn.json文件" << std::endl;
                return false;
            }

            std::string jsonContent;
            std::stringstream buffer;
            buffer << rulesFile.rdbuf();
            jsonContent = buffer.str();
            rulesFile.close();

            std::cout << "文件内容读取完成，开始解析JSON..." << std::endl;
            rules = json::parse(jsonContent);
            
            std::cout << "JSON解析成功，开始验证规则格式..." << std::endl;
            if (!validateRules(rules)) {
                return false;
            }

            return true;
        } catch (const json::parse_error& e) {
            std::cerr << "JSON解析错误: " << e.what() << std::endl;
            std::cerr << "错误位置: 行 " << e.byte << std::endl;
            return false;
        } catch (const std::exception& e) {
            std::cerr << "加载规则时发生错误: " << e.what() << std::endl;
            return false;
        }
    }

public:
    TypeConnAnalyzer() {
        std::cout << "正在初始化TypeConnAnalyzer..." << std::endl;
        
        conn = mysql_init(NULL);
        if (conn == NULL) {
            throw std::runtime_error("MySQL初始化失败");
        }
        std::cout << "MySQL初始化成功" << std::endl;

        std::string host, user, password, database;
        std::cout << "加载数据库配置文件..." << std::endl;
        if (!loadConfig(host, user, password, database)) {
            throw std::runtime_error("加载数据库配置失败");
        }
        std::cout << "配置加载成功" << std::endl;

        if (!mysql_real_connect(conn, host.c_str(), user.c_str(), password.c_str(), 
                             database.c_str(), 0, NULL, 0)) {
            std::string error = mysql_error(conn);
            throw std::runtime_error("连接MySQL失败: " + error);
        }
        
        if (mysql_set_character_set(conn, "utf8mb4")) {
            std::string error = mysql_error(conn);
            throw std::runtime_error("设置字符集失败: " + error);
        }
        std::cout << "成功连接到MySQL数据库，字符集设置为 utf8mb4" << std::endl;

        // 数据库连接成功后再加载规则
        if (!loadRules()) {
            throw std::runtime_error("规则加载失败");
        }
        std::cout << "规则加载成功" << std::endl;
    }

    ~TypeConnAnalyzer() {
        if (conn) {
            mysql_close(conn);
        }
    }

    bool processConnections() {
        if (!conn || !rules.contains("rules")) {
            std::cerr << "数据库连接或规则未正确初始化" << std::endl;
            return false;
        }

        // 设置 MySQL 连接的字符集为 UTF-8
        mysql_set_character_set(conn, "utf8mb4");
        
        std::cout << "开始处理连接..." << std::endl;
        std::string query = "SELECT id, terminal_list FROM panel_types";
        
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
            std::string updateQuery = "UPDATE panel_types SET inner_conn_list = ? WHERE id = ?";
            
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
    try {
        TypeConnAnalyzer analyzer;
        if (!analyzer.processConnections()) {
            std::cerr << "处理连接失败" << std::endl;
            return 1;
        }
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "程序执行发生错误: " << e.what() << std::endl;
        return 1;
    }
}