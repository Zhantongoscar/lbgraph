#include <mysql.h>
#include <iostream>
#include <string>
#include <vector>
#include <set>
#include <fstream>
#include <sstream>

class TypeConnAnalyzer {
private:
    MYSQL* conn;
    std::string typesTableName;

    bool loadConfig(std::string& host, std::string& user, std::string& password, std::string& database) {
        std::ifstream configFile("config.json");
        if (!configFile.is_open()) {
            std::cerr << "无法打开配置文件" << std::endl;
            return false;
        }

        std::string line;
        std::string jsonStr;
        while (std::getline(configFile, line)) {
            jsonStr += line;
        }
        configFile.close();

        // 先定位mysql部分
        size_t mysqlStart = jsonStr.find("\"mysql\"");
        if (mysqlStart == std::string::npos) {
            std::cerr << "配置文件中未找到MySQL配置" << std::endl;
            return false;
        }
        
        // 找到mysql对象的结束位置
        size_t mysqlEnd = jsonStr.find("}", mysqlStart);
        if (mysqlEnd == std::string::npos) {
            std::cerr << "MySQL配置格式错误" << std::endl;
            return false;
        }
        
        // 只在mysql部分中查找配置
        std::string mysqlConfig = jsonStr.substr(mysqlStart, mysqlEnd - mysqlStart);

        size_t pos = mysqlConfig.find("\"host\"");
        if (pos != std::string::npos) {
            size_t start = mysqlConfig.find("\"", pos + 6) + 1;
            size_t end = mysqlConfig.find("\"", start);
            host = mysqlConfig.substr(start, end - start);
        }

        pos = mysqlConfig.find("\"user\"");
        if (pos != std::string::npos) {
            size_t start = mysqlConfig.find("\"", pos + 6) + 1;
            size_t end = mysqlConfig.find("\"", start);
            user = mysqlConfig.substr(start, end - start);
        }

        pos = mysqlConfig.find("\"password\"");
        if (pos != std::string::npos) {
            size_t start = mysqlConfig.find("\"", pos + 10) + 1;
            size_t end = mysqlConfig.find("\"", start);
            password = mysqlConfig.substr(start, end - start);
        }

        pos = mysqlConfig.find("\"database\"");
        if (pos != std::string::npos) {
            size_t start = mysqlConfig.find("\"", pos + 10) + 1;
            size_t end = mysqlConfig.find("\"", start);
            database = mysqlConfig.substr(start, end - start);
        }

        return true;
    }

    std::string escapeString(const std::string& str) {
        char* escaped = new char[str.length() * 2 + 1];
        mysql_real_escape_string(conn, escaped, str.c_str(), str.length());
        std::string result(escaped);
        delete[] escaped;
        return result;
    }

    // 分析端子列表查找可能的连接
    std::string analyzeTerminals(const std::vector<std::string>& terminals) {
        std::stringstream connections;
        std::set<std::string> processedPairs;
        bool firstConn = true;

        connections << "[";

        for (size_t i = 0; i < terminals.size(); i++) {
            for (size_t j = i + 1; j < terminals.size(); j++) {
                const std::string& t1 = terminals[i];
                const std::string& t2 = terminals[j];

                // 检查A1-A2配对
                if ((t1 == "A1" && t2 == "A2") || (t1 == "A2" && t2 == "A1")) {
                    std::string pair = t1 < t2 ? t1 + "-" + t2 : t2 + "-" + t1;
                    if (processedPairs.find(pair) == processedPairs.end()) {
                        if (!firstConn) connections << ",";
                        connections << "\n      {";
                        connections << "\"from\":\"" << t1 << "\",";
                        connections << "\"to\":\"" << t2 << "\",";
                        connections << "\"type\":\"coil_connection\",";
                        connections << "\"description\":\"线圈连接\"";
                        connections << "}";
                        processedPairs.insert(pair);
                        firstConn = false;
                    }
                }
                // 检查触点组连接（如11-12-14）
                else if (t1.length() == 2 && t2.length() == 2 && 
                         t1[0] == t2[0] && std::isdigit(t1[0])) {
                    std::string pair = t1 < t2 ? t1 + "-" + t2 : t2 + "-" + t1;
                    if (processedPairs.find(pair) == processedPairs.end()) {
                        if (!firstConn) connections << ",";
                        connections << "\n      {";
                        connections << "\"from\":\"" << t1 << "\",";
                        connections << "\"to\":\"" << t2 << "\",";
                        connections << "\"type\":\"contact_connection\",";
                        connections << "\"description\":\"触点组" << t1[0] << "连接\"";
                        connections << "}";
                        processedPairs.insert(pair);
                        firstConn = false;
                    }
                }
            }
        }

        connections << "\n    ]";
        return connections.str();
    }

public:
    TypeConnAnalyzer() : typesTableName("panel_types") {
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

    bool generateConnectionRules() {
        std::cout << "开始生成连接规则..." << std::endl;
        std::string query = "SELECT type, terminal_list FROM " + typesTableName;
        std::cout << "执行查询: " << query << std::endl;
        
        if (mysql_query(conn, query.c_str())) {
            std::cerr << "查询失败: " << mysql_error(conn) << std::endl;
            return false;
        }
        std::cout << "查询执行成功" << std::endl;

        MYSQL_RES* result = mysql_store_result(conn);
        if (!result) {
            std::cerr << "获取结果失败: " << mysql_error(conn) << std::endl;
            return false;
        }
        std::cout << "成功获取查询结果" << std::endl;

        // 开始构建JSON字符串
        std::stringstream allRules;
        allRules << "{\n  \"types\": [";
        bool firstType = true;

        MYSQL_ROW row;
        while ((row = mysql_fetch_row(result))) {
            std::string type = row[0];
            std::string terminalListStr = row[1];

            // 解析terminal_list（JSON数组格式）
            std::vector<std::string> terminals;
            size_t pos = 0;
            while ((pos = terminalListStr.find("\"", pos)) != std::string::npos) {
                pos++; // 跳过开头的引号
                size_t endPos = terminalListStr.find("\"", pos);
                if (endPos != std::string::npos) {
                    terminals.push_back(terminalListStr.substr(pos, endPos - pos));
                    pos = endPos + 1;
                }
            }

            if (!firstType) allRules << ",";
            allRules << "\n    {\n";
            allRules << "      \"type\": \"" << type << "\",\n";
            allRules << "      \"connections\": ";
            allRules << analyzeTerminals(terminals);
            allRules << "\n    }";
            firstType = false;
        }

        allRules << "\n  ]\n}";

        mysql_free_result(result);

        // 保存到文件
        std::ofstream rulesFile("c2_rules_type_conn.json");
        if (!rulesFile.is_open()) {
            std::cerr << "无法创建c2_rules_type_conn.json文件" << std::endl;
            return false;
        }

        rulesFile << allRules.str();
        rulesFile.close();

        std::cout << "连接规则已生成并保存到c2_rules_type_conn.json" << std::endl;
        return true;
    }
};

int main() {
    TypeConnAnalyzer analyzer;
    if (!analyzer.generateConnectionRules()) {
        std::cerr << "生成连接规则失败" << std::endl;
        return 1;
    }
    return 0;
}