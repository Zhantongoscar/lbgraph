#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <map>
#include <set>
#include <algorithm>
#include <windows.h>
#include "C:/clib/mysql/include/mysql.h"

// 简单的JSON解析函数
std::string getValueFromJson(const std::string& jsonStr, const std::string& key) {
    size_t pos = jsonStr.find("\"" + key + "\"");
    if (pos == std::string::npos) return "";
    
    pos = jsonStr.find(":", pos);
    if (pos == std::string::npos) return "";
    
    pos = jsonStr.find("\"", pos);
    if (pos == std::string::npos) return "";
    
    size_t start = pos + 1;
    size_t end = jsonStr.find("\"", start);
    if (end == std::string::npos) return "";
    
    return jsonStr.substr(start, end - start);
}

// 设备类型结构体
struct DeviceType {
    int id;
    std::string device;         // 设备标识符（现在是第二个字段）
    std::string project_number;  // 项目编号
    std::string type;           // 设备类型
    std::string function;       // = 和 + 之间的内容
    std::string location;       // + 和第一个 - 之间的内容
    std::string terminal_list;  // JSON格式的终端列表
    std::string inner_list;     // JSON格式的内部连接列表
};

class PanelDeviceTable {
private:
    MYSQL* conn;
    std::string tableName;
    std::string typesTableName;  // 添加类型表名
    std::string csvPath;
    std::string projectNumber;
    int typeCounter;  // 用于生成唯一的类型名

    // 从config.json读取配置
    bool loadConfig(std::string& host, std::string& user, std::string& password, std::string& database) {
        try {
            std::cout << "尝试打开config.json..." << std::endl;
            std::ifstream configFile("config.json");
            if (!configFile.is_open()) {
                std::cerr << "无法打开config.json文件" << std::endl;
                return false;
            }
            std::cout << "成功打开config.json" << std::endl;

            std::string jsonStr;
            std::string line;
            while (std::getline(configFile, line)) {
                jsonStr += line;
            }

            // 从mysql节点下获取配置
            std::string mysqlJson = jsonStr.substr(jsonStr.find("\"mysql\""));
            mysqlJson = mysqlJson.substr(0, mysqlJson.find("}") + 1);
            
            host = getValueFromJson(mysqlJson, "host");
            user = getValueFromJson(mysqlJson, "user");
            password = getValueFromJson(mysqlJson, "password");
            database = getValueFromJson(mysqlJson, "database");

            // 从files节点下获取配置
            std::string filesJson = jsonStr.substr(jsonStr.find("\"files\""));
            filesJson = filesJson.substr(0, filesJson.find("}") + 1);
            
            csvPath = getValueFromJson(filesJson, "csv_path");
            projectNumber = getValueFromJson(filesJson, "project_number");

            std::cout << "配置信息：" << std::endl;
            std::cout << "CSV路径: " << csvPath << std::endl;
            std::cout << "项目编号: " << projectNumber << std::endl;

            return !host.empty() && !user.empty() && !password.empty() && !database.empty() 
                   && !csvPath.empty() && !projectNumber.empty();
        }
        catch (const std::exception& e) {
            std::cerr << "读取配置文件错误: " << e.what() << std::endl;
            return false;
        }
    }

    // 辅助函数：安全地转义字符串
    std::string escapeString(const std::string& str) {
        size_t bufLen = str.length() * 2 + 1;  // MySQL 文档建议的缓冲区大小
        std::vector<char> buffer(bufLen);
        unsigned long length = mysql_real_escape_string(conn, buffer.data(), str.c_str(), str.length());
        return std::string(buffer.data(), length);
    }

    // 从字符串中提取指定分隔符之间的内容
    std::string extractBetween(const std::string& str, const std::string& start, const std::string& end) {
        size_t startPos = str.find(start);
        if (startPos == std::string::npos) return "";
        startPos += start.length();
        
        size_t endPos = str.find(end, startPos);
        if (endPos == std::string::npos) return "";
        
        return str.substr(startPos, endPos - startPos);
    }

    // 从字符串中提取设备标识符和端口号
    std::pair<std::string, std::string> extractDeviceAndPort(const std::string& str) {
        // 查找冒号位置
        size_t colonPos = str.find(":");
        if (colonPos == std::string::npos) {
            return std::make_pair(str, "1"); // 如果没有冒号，返回默认端口号"1"
        }

        return std::make_pair(
            str.substr(0, colonPos),        // 设备标识符（保留开头的=）
            str.substr(colonPos + 1)        // 端口号
        );
    }

    // 解析设备信息
    void parseDeviceInfo(const std::string& str, DeviceType& device) {
        std::cout << "\n解析设备信息: " << str << std::endl;
        
        // 提取设备标识符和端口号
        auto [deviceId, port] = extractDeviceAndPort(str);
        std::cout << "原始设备ID: " << deviceId << ", 端口: " << port << std::endl;
        
        // 提取 function 和 location
        size_t equalPos = deviceId.find("=");
        if (equalPos != std::string::npos) {
            size_t plusPos = deviceId.find("+", equalPos);
            if (plusPos != std::string::npos) {
                // 提取 function (= 到第一个 + 之间的内容)
                device.function = deviceId.substr(equalPos + 1, plusPos - (equalPos + 1));
                std::cout << "提取到 function: " << device.function << std::endl;
                
                // 提取 location (第一个 + 到第一个 - 之间的内容)
                size_t minusPos = deviceId.find("-", plusPos);
                if (minusPos != std::string::npos) {
                    device.location = deviceId.substr(plusPos + 1, minusPos - (plusPos + 1));
                    std::cout << "提取到 location: " << device.location << std::endl;
                    device.device = deviceId.substr(1);  // 去掉开头的等号
                } else {
                    std::cout << "未找到 '-' 符号，无法提取 location" << std::endl;
                    device.device = deviceId.substr(1);  // 去掉开头的等号
                }
            } else {
                std::cout << "未找到 '+' 符号，无法提取 function 和 location" << std::endl;
                device.device = deviceId.substr(1);  // 去掉开头的等号
            }
        } else {
            std::cout << "未找到 '=' 符号，无法提取 function 和 location" << std::endl;
            device.device = deviceId;  // 没有等号，使用原始ID
        }

        std::cout << "最终设备ID: " << device.device << std::endl;

        // 创建简化的 terminal_list（使用JSON数组）
        device.terminal_list = "[\"" + port + "\"]";
        std::cout << "生成的 terminal_list: " << device.terminal_list << std::endl;
    }

    // 检查设备是否存在
    bool deviceExists(const std::string& deviceId, std::string& existingTerminalList) {
        std::string query = "SELECT terminal_list FROM " + tableName + 
                          " WHERE device = '" + escapeString(deviceId) + "'";
        
        if (mysql_query(conn, query.c_str()) != 0) {
            std::cerr << "查询设备失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        MYSQL_RES* result = mysql_store_result(conn);
        if (result == NULL) {
            std::cerr << "获取结果失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        MYSQL_ROW row = mysql_fetch_row(result);
        if (row) {
            existingTerminalList = row[0] ? row[0] : ""; 
            mysql_free_result(result);
            return true;
        }

        mysql_free_result(result);
        return false;
    }

    // 更新设备的端口列表
    bool updateDeviceTerminals(const std::string& deviceId, const std::string& newPort) {
        std::string existingTerminalList;
        if (!deviceExists(deviceId, existingTerminalList)) {
            return false;
        }

        // 解析现有的 terminal_list（数组格式）
        std::vector<std::string> ports;
        size_t pos = 0;
        while ((pos = existingTerminalList.find("\"", pos)) != std::string::npos) {
            pos++; // 跳过开头的引号
            size_t endPos = existingTerminalList.find("\"", pos);
            if (endPos != std::string::npos) {
                std::string port = existingTerminalList.substr(pos, endPos - pos);
                if (std::find(ports.begin(), ports.end(), port) == ports.end()) {
                    ports.push_back(port);
                }
                pos = endPos + 1;
            }
        }

        // 检查新端口是否已存在
        auto it = std::find(ports.begin(), ports.end(), newPort);
        if (it == ports.end()) {
            ports.push_back(newPort);
        }

        // 构建新的 terminal_list（简单数组格式）
        std::string newTerminalList = "[";
        for (size_t i = 0; i < ports.size(); ++i) {
            if (i > 0) newTerminalList += ",";
            newTerminalList += "\"" + ports[i] + "\"";
        }
        newTerminalList += "]";

        // 更新数据库
        std::string query = "UPDATE " + tableName + 
                          " SET terminal_list = '" + escapeString(newTerminalList) + "'" +
                          " WHERE device = '" + escapeString(deviceId) + "'";

        return mysql_query(conn, query.c_str()) == 0;
    }

    // 初始化类型表
    bool initializeTypesTable() {
        std::cout << "初始化类型表..." << std::endl;
        
        // 检查表是否存在
        std::string checkTable = "SHOW TABLES LIKE '" + typesTableName + "'";
        if (mysql_query(conn, checkTable.c_str())) {
            std::cerr << "检查类型表失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        MYSQL_RES* result = mysql_store_result(conn);
        if (result == NULL) {
            std::cerr << "获取结果失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        bool tableExists = (mysql_num_rows(result) > 0);
        mysql_free_result(result);

        if (!tableExists) {
            std::cout << "创建类型表..." << std::endl;
            // 创建表时先不添加唯一约束，我们通过程序逻辑来确保唯一性
            std::string createTable = "CREATE TABLE " + typesTableName + " ("
                "id INT PRIMARY KEY AUTO_INCREMENT, "
                "type VARCHAR(255) NOT NULL UNIQUE, "
                "terminal_list JSON, "
                "inner_conn_list JSON"
                ") CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci";

            if (mysql_query(conn, createTable.c_str())) {
                std::cerr << "创建类型表失败: " << mysql_error(conn) << std::endl;
                return false;
            }
            std::cout << "成功创建类型表" << std::endl;

            // 创建一个触发器来防止重复的terminal_list
            std::string createTrigger = "CREATE TRIGGER prevent_duplicate_terminal_list "
                                      "BEFORE INSERT ON " + typesTableName + " "
                                      "FOR EACH ROW "
                                      "BEGIN "
                                      "    IF EXISTS (SELECT 1 FROM " + typesTableName + " WHERE terminal_list = NEW.terminal_list) THEN "
                                      "        SIGNAL SQLSTATE '45000' "
                                      "        SET MESSAGE_TEXT = 'Duplicate terminal_list is not allowed'; "
                                      "    END IF; "
                                      "END;";

            if (mysql_query(conn, createTrigger.c_str())) {
                std::cerr << "创建触发器失败: " << mysql_error(conn) << std::endl;
                // 即使触发器创建失败，我们也继续执行，因为我们还有程序层面的检查
            } else {
                std::cout << "成功创建防重复触发器" << std::endl;
            }
        }

        // 获取当前最大的类型编号
        std::string getMaxType = "SELECT MAX(CAST(SUBSTRING(type, 5) AS UNSIGNED)) FROM " + typesTableName + 
                                " WHERE type REGEXP '^TYPE[0-9]+$'";
        if (mysql_query(conn, getMaxType.c_str())) {
            std::cerr << "获取最大类型编号失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        result = mysql_store_result(conn);
        if (result == NULL) {
            std::cerr << "获取结果失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        MYSQL_ROW row = mysql_fetch_row(result);
        typeCounter = row[0] ? std::stoi(row[0]) : 0;
        mysql_free_result(result);

        return true;
    }

    // 查找匹配的类型
    std::string findMatchingType(const std::string& terminalList) {
        std::string query = "SELECT type FROM " + typesTableName + 
                          " WHERE terminal_list = '" + escapeString(terminalList) + "'";
        
        if (mysql_query(conn, query.c_str())) {
            std::cerr << "查询类型失败: " << mysql_error(conn) << std::endl;
            return "";
        }

        MYSQL_RES* result = mysql_store_result(conn);
        if (result == NULL) {
            std::cerr << "获取结果失败: " << mysql_error(conn) << std::endl;
            return "";
        }

        MYSQL_ROW row = mysql_fetch_row(result);
        std::string type = row ? row[0] : "";
        mysql_free_result(result);
        
        return type;
    }

    // 创建新类型
    std::string createNewType(const std::string& terminalList) {
        // 首先检查是否已存在相同的 terminal_list 特征
        std::string query = "SELECT type FROM " + typesTableName + 
                          " WHERE terminal_list = '" + escapeString(terminalList) + "'";
        
        if (mysql_query(conn, query.c_str())) {
            std::cerr << "查询类型特征失败: " << mysql_error(conn) << std::endl;
            return "";
        }

        MYSQL_RES* result = mysql_store_result(conn);
        if (result == NULL) {
            std::cerr << "获取结果失败: " << mysql_error(conn) << std::endl;
            return "";
        }

        MYSQL_ROW row = mysql_fetch_row(result);
        if (row) {
            // 已存在相同特征的类型，直接返回该类型
            std::string existingType = row[0];
            mysql_free_result(result);
            std::cout << "找到已存在的相同特征类型: " << existingType << std::endl;
            return existingType;
        }
        mysql_free_result(result);

        // 如果不存在相同特征，创建新类型
        typeCounter++;
        std::string newType = "TYPE" + std::to_string(typeCounter);
        std::cout << "创建新特征类型: " << newType << std::endl;
        
        query = "INSERT INTO " + typesTableName + 
                " (type, terminal_list, inner_conn_list) VALUES ("
                "'" + escapeString(newType) + "', "
                "'" + escapeString(terminalList) + "', "
                "'{}')"
                " ON DUPLICATE KEY UPDATE type = type";  // 防止类型名重复

        if (mysql_query(conn, query.c_str())) {
            std::cerr << "创建新类型失败: " << mysql_error(conn) << std::endl;
            return "";
        }

        return newType;
    }

    // 更新设备类型
    bool updateDeviceType(const std::string& deviceId, const std::string& type) {
        std::string query = "UPDATE " + tableName + 
                          " SET type = '" + escapeString(type) + "'" +
                          " WHERE device = '" + escapeString(deviceId) + "'";

        return mysql_query(conn, query.c_str()) == 0;
    }

    // 计算设备的端子数量
    int countDevicePorts(const std::string& terminalList) {
        int count = 0;
        size_t pos = 0;
        while ((pos = terminalList.find("\"", pos)) != std::string::npos) {
            count++;
            pos = terminalList.find("\"", pos + 1);
            if (pos != std::string::npos) pos++;
        }
        return count / 2; // 因为每个端口有两个引号
    }

    // 更新内部连接列表
    bool updateInnerConnections() {
        std::cout << "\n开始更新内部连接列表..." << std::endl;
        std::cout << "updateInnerConnections called" << std::endl;

        // 获取所有带有type的记录
        std::string query = "SELECT type, terminal_list, inner_conn_list FROM " + typesTableName +
                          " WHERE type IS NOT NULL";

        if (mysql_query(conn, query.c_str())) {
            std::cerr << "查询类型失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        MYSQL_RES* result = mysql_store_result(conn);
        if (!result) {
            std::cerr << "获取结果失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        // 加载连接规则
        std::ifstream rulesFile("conn_rules.json");
        if (!rulesFile.is_open()) {
            std::cerr << "无法打开conn_rules.json文件" << std::endl;
            std::cout << "Failed to open conn_rules.json" << std::endl;
            mysql_free_result(result);
            return false;
        }

        std::cout << "conn_rules.json opened successfully" << std::endl;

        std::string jsonStr((std::istreambuf_iterator<char>(rulesFile)),
                           std::istreambuf_iterator<char>());
        rulesFile.close();

        bool success = true;
        MYSQL_ROW row;
        while ((row = mysql_fetch_row(result))) {
            std::string type = row[0];
            std::string terminalList = row[1];
            std::string innerList = row[2] ? row[2] : "{}";

            std::cout << "\n处理类型: " << type << std::endl;
            std::cout << "当前terminal_list: " << terminalList << std::endl;
            std::cout << "当前inner_list: " << innerList << std::endl;

            // 提取terminal_list中的端口
            std::vector<std::string> ports;
            size_t pos = 0;
            while ((pos = terminalList.find("\"", pos)) != std::string::npos) {
                pos++; // 跳过开头的引号
                size_t endPos = terminalList.find("\"", pos);
                if (endPos != std::string::npos) {
                    std::string port = terminalList.substr(pos, endPos - pos);
                    ports.push_back(port);
                    std::cout << "找到端口: " << port << std::endl;
                    pos = endPos + 1;
                }
            }

            // 检查是否需要更新
            if (innerList != "{}") {
                std::cout << "inner_list已存在，跳过处理" << std::endl;
                continue;
            }

            // 检查是否有匹配的规则
            bool hasMatch = false;
            std::string newInnerList = "{\"connections\":[";
            bool firstConnection = true;

            for (size_t i = 0; i < ports.size(); ++i) {
                for (size_t j = i + 1; j < ports.size(); ++j) {
                    std::string port1 = ports[i];
                    std::string port2 = ports[j];
                    std::cout << "Checking ports " << port1 << " and " << port2 << std::endl;

                    // 在rules数组中查找匹配的规则
                    size_t rulesStart = jsonStr.find("[");
                    size_t rulesEnd = jsonStr.find_last_of("]");
                    if (rulesStart != std::string::npos && rulesEnd != std::string::npos) {
                        std::string rulesStr = jsonStr.substr(rulesStart + 1, rulesEnd - rulesStart - 1);
                        std::istringstream ruleStream(rulesStr);
                        std::string rule;

                        while (std::getline(ruleStream, rule, '}')) {
                            std::cout << "Processing rule: " << rule << std::endl;
                            if (rule.find("{") != std::string::npos) {
                                // 提取规则中的端口
                                size_t portsStart = rule.find("\"ports\"");
                                if (portsStart != std::string::npos) {
                                    size_t arrayStart = rule.find("[", portsStart);
                                    size_t arrayEnd = rule.find("]", arrayStart);
                                    if (arrayStart != std::string::npos && arrayEnd != std::string::npos) {
                                        std::string portsStr = rule.substr(arrayStart + 1, arrayEnd - arrayStart - 1);
                                        std::cout << "portsStr: " << portsStr << std::endl;
                                        std::vector<std::string> rulePorts;

                                        // 解析规则端口
                                        std::istringstream portStream(portsStr);
                                        std::string rulePort;
                                        while (std::getline(portStream, rulePort, ',')) {
                                            // 移除引号和空格
                                            rulePort.erase(std::remove_if(rulePort.begin(), rulePort.end(), 
                                                         [](char c) { return c == '"' || c == ' '; }), rulePort.end());
                                            rulePorts.push_back(rulePort);
                                            std::cout << "规则端口: " << rulePort << std::endl;
                                        }

                                        // 检查是否所有规则端口都存在于设备端口中
                                        bool allPortsFound = true;
                                        for (const auto& rulePort : rulePorts) {
                                            auto it = std::find(ports.begin(), ports.end(), rulePort);
                                            if (it == ports.end()) {
                                                allPortsFound = false;
                                                std::cout << "规则端口 " << rulePort << " 不存在于设备端口中" << std::endl;
                                                break;
                                            }
                                        }

                                        if (allPortsFound && rulePorts.size() >= 2) {
                                            std::cout << "找到匹配的端口规则" << std::endl;
                                            // 提取属性和方向
                                            std::string property = getValueFromJson(rule, "property");
                                            std::string direction = getValueFromJson(rule, "direction");

                                            if (!firstConnection) {
                                                newInnerList += ",";
                                            }
                                            firstConnection = false;

                                            // 添加连接
                                            newInnerList += "{\"from\":\"" + rulePorts[0] + 
                                                          "\",\"to\":\"" + rulePorts[1] + 
                                                          "\",\"property\":\"" + property + 
                                                          "\",\"direction\":\"" + direction + "\"}";
                                            hasMatch = true;
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            newInnerList += "]}";

            // 如果找到匹配的规则，更新数据库
            if (hasMatch) {
                std::string updateQuery = "UPDATE " + typesTableName + 
                                       " SET inner_conn_list = '" + escapeString(newInnerList) + "'" +
                                       " WHERE type = '" + escapeString(type) + "'";
                
                if (mysql_query(conn, updateQuery.c_str())) {
                    std::cerr << "更新inner_list失败: " << mysql_error(conn) << std::endl;
                    success = false;
                    break;
                }
                std::cout << "更新inner_list为: " << newInnerList << std::endl;
            } else {
                std::cout << "没有找到匹配的规则" << std::endl;
            }
        }

        mysql_free_result(result);
        return success;
    }

public:
    PanelDeviceTable(const std::string& table) 
        : tableName(table), typesTableName("panel_types"), typeCounter(0) {
        std::cout << "初始化MySQL客户端..." << std::endl;
        conn = mysql_init(NULL);
        if (conn == NULL) {
            std::cerr << "MySQL初始化失败: " << mysql_error(NULL) << std::endl;
            return;
        }
        std::cout << "MySQL客户端初始化成功" << std::endl;
        

        std::string host, user, password, database;
        std::cout << "读取配置文件..." << std::endl;
        if (!loadConfig(host, user, password, database)) {
            std::cerr << "加载配置失败" << std::endl;
            return;
        }
        std::cout << "配置文件读取成功" << std::endl;
        std::cout << "正在连接到MySQL服务器: " << host << ", 数据库: " << database << std::endl;

        // 连接MySQL数据库
        if (!mysql_real_connect(conn, host.c_str(), user.c_str(), password.c_str(),
                              database.c_str(), 0, NULL, 0)) {
            std::cerr << "连接数据库失败: " << mysql_error(conn) << std::endl;
            return;
        }
        std::cout << "成功连接到MySQL服务器" << std::endl;

        // 设置字符集
        mysql_set_character_set(conn, "utf8");

        // 先尝试删除已存在的表
        std::string dropTable = "DROP TABLE IF EXISTS " + tableName;
        if (mysql_query(conn, dropTable.c_str())) {
            std::cerr << "删除表失败: " << mysql_error(conn) << std::endl;
            return;
        }
        std::cout << "已删除旧表（如果存在）" << std::endl;

        // 创建新表，调整字段顺序
        std::string createTable = "CREATE TABLE " + tableName + " ("
            "id INT PRIMARY KEY AUTO_INCREMENT, "
            "device VARCHAR(255) NOT NULL, "
            "project_number VARCHAR(255) NOT NULL, "
            "type VARCHAR(255), "
            "function TEXT, "
            "location TEXT, "
            "terminal_list JSON, "
            "inner_list JSON"
            ") CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci";
        
        if (mysql_query(conn, createTable.c_str())) {
            std::cerr << "创建表失败: " << mysql_error(conn) << std::endl;
            return;
        }
        std::cout << "成功创建表结构" << std::endl;

        // 验证表结构
        if (mysql_query(conn, ("DESCRIBE " + tableName).c_str())) {
            std::cerr << "获取表结构失败: " << mysql_error(conn) << std::endl;
            return;
        }
        
        MYSQL_RES* result = mysql_store_result(conn);
        if (result == NULL) {
            std::cerr << "存储表结构结果失败: " << mysql_error(conn) << std::endl;
            return;
        }

        std::cout << "\n表结构：" << std::endl;
        std::cout << "----------------------------------------" << std::endl;
        MYSQL_ROW row;
        while ((row = mysql_fetch_row(result))) {
            std::cout << "字段: " << row[0] << ", 类型: " << row[1] << ", 是否为空: " << row[2] 
                      << ", 键: " << row[3] << ", 默认值: " << row[4] << ", 额外: " << row[5] << std::endl;
        }
        std::cout << "----------------------------------------" << std::endl;
        mysql_free_result(result);

        // 初始化类型表
        if (!initializeTypesTable()) {
            std::cerr << "初始化类型表失败" << std::endl;
            return;
        }

        // 从CSV导入数据，使用配置文件中的路径和项目编号
        std::cout << "\n尝试从CSV导入数据..." << std::endl;
        if (importFromCSV(csvPath, projectNumber)) {
            std::cout << "数据导入成功" << std::endl;

            // 处理设备类型匹配
            std::cout << "\n处理设备类型匹配..." << std::endl;
            if (processDeviceTypes()) {
                std::cout << "设备类型处理成功" << std::endl;
            } else {
                std::cout << "设备类型处理失败" << std::endl;
            }
        } else {
            std::cout << "数据导入失败" << std::endl;
        }

        // 更新内部连接列表
        std::cout << "\n处理内部连接..." << std::endl;
        if (updateInnerConnections()) {
            std::cout << "内部连接更新成功" << std::endl;
        } else {
            std::cout << "内部连接更新失败" << std::endl;
        }

        // 显示结果
        displayDevicePorts();

        std::cout << "\n程序执行完成" << std::endl;
    }

    ~PanelDeviceTable() {
        if (conn) {
            mysql_close(conn);
        }
    }

    // 从CSV导入数据
    bool importFromCSV(const std::string& path, const std::string& projectNumber) {
        std::cout << "CSV路径: " << path << std::endl;
        std::cout << "项目编号: " << projectNumber << std::endl;

        std::ifstream csvFile(path);
        if (!csvFile.is_open()) {
            std::cerr << "无法打开CSV文件: " << path << std::endl;
            return false;
        }

        std::string line;
        std::getline(csvFile, line); // 跳过标题行

        while (std::getline(csvFile, line)) {
            std::istringstream lineStream(line);
            std::string deviceInfo;
            std::getline(lineStream, deviceInfo, ',');

            DeviceType device;
            parseDeviceInfo(deviceInfo, device);
            device.project_number = projectNumber;

            // 插入设备信息到数据库
            std::string query = "INSERT INTO " + tableName + 
                              " (device, project_number, type, function, location, terminal_list, inner_list) VALUES ("
                              "'" + escapeString(device.device) + "', "
                              "'" + escapeString(device.project_number) + "', "
                              "'" + escapeString(device.type) + "', "
                              "'" + escapeString(device.function) + "', "
                              "'" + escapeString(device.location) + "', "
                              "'" + escapeString(device.terminal_list) + "', "
                              "'" + escapeString(device.inner_list) + "')"
                              " ON DUPLICATE KEY UPDATE device = device";

            if (mysql_query(conn, query.c_str())) {
                std::cerr << "插入设备信息失败: " << mysql_error(conn) << std::endl;
                return false;
            }
        }

        return true;
    }

    // 处理设备类型匹配
    bool processDeviceTypes() {
        std::string query = "SELECT device, terminal_list FROM " + tableName;
        if (mysql_query(conn, query.c_str())) {
            std::cerr << "查询设备失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        MYSQL_RES* result = mysql_store_result(conn);
        if (!result) {
            std::cerr << "获取结果失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        MYSQL_ROW row;
        while ((row = mysql_fetch_row(result))) {
            std::string deviceId = row[0];
            std::string terminalList = row[1];

            std::cout << "\n处理设备: " << deviceId << std::endl;
            std::cout << "当前terminal_list: " << terminalList << std::endl;

            // 查找匹配的类型
            std::string type = findMatchingType(terminalList);
            if (type.empty()) {
                // 如果没有匹配的类型，创建新类型
                type = createNewType(terminalList);
            }

            // 更新设备类型
            if (!updateDeviceType(deviceId, type)) {
                std::cerr << "更新设备类型失败: " << mysql_error(conn) << std::endl;
                mysql_free_result(result);
                return false;
            }
        }

        mysql_free_result(result);
        return true;
    }

    // 显示设备端子数量
    void displayDevicePorts() {
        std::string query = "SELECT device, terminal_list FROM " + tableName;
        if (mysql_query(conn, query.c_str())) {
            std::cerr << "查询设备失败: " << mysql_error(conn) << std::endl;
            return;
        }

        MYSQL_RES* result = mysql_store_result(conn);
        if (!result) {
            std::cerr << "获取结果失败: " << mysql_error(conn) << std::endl;
            return;
        }

        MYSQL_ROW row;
        while ((row = mysql_fetch_row(result))) {
            std::string deviceId = row[0];
            std::string terminalList = row[1];
            int portCount = countDevicePorts(terminalList);

            std::cout << "\n设备: " << deviceId << std::endl;
            std::cout << "端子数量: " << portCount << std::endl;
        }

        mysql_free_result(result);
    }
};

int main() {
    // 设置控制台输出为UTF-8
    SetConsoleOutputCP(CP_UTF8);
    // 禁用stdout缓冲
    setbuf(stdout, NULL);

    std::cout << "程序开始执行..." << std::endl;
    PanelDeviceTable table("panel_device_inner");

    std::cout << "\n程序执行完成" << std::endl;
    return 0;
}
