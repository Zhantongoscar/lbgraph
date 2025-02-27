#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <map>
#include <windows.h>
#include "C:/clib/mysql/include/mysql.h"

// 连接结构
struct V_Connection {
    std::string connNo;         // 图纸连接号
    std::string source;         // 完整点设备标识符
    std::string target;         // 完整点的目标设备标识符
    std::string color;          // 颜色
    bool isCable;               // 属于电缆
    std::string connType;       // 类型（内部线圈 内部触点常开 内部触点常闭 外部连接）
    double voltage;             // 电压
    double current;             // 电流
    double resistance;          // 电阻
};

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

class ConnectionImporter {
private:
    MYSQL* conn;
    std::string tableName;
    std::string csvPath;
    std::string projectNumber;

    // 从config.json读取配置
    bool loadConfig(std::string& host, std::string& user, std::string& password, std::string& database) {
        try {
            std::ifstream configFile("config.json");
            if (!configFile.is_open()) {
                std::cerr << "无法打开config.json文件" << std::endl;
                return false;
            }

            std::string jsonStr;
            std::string line;
            while (std::getline(configFile, line)) {
                jsonStr += line;
            }

            // 读取MySQL配置
            std::string mysqlJson = jsonStr.substr(jsonStr.find("\"mysql\""));
            mysqlJson = mysqlJson.substr(0, mysqlJson.find("}") + 1);
            
            host = getValueFromJson(mysqlJson, "host");
            user = getValueFromJson(mysqlJson, "user");
            password = getValueFromJson(mysqlJson, "password");
            database = getValueFromJson(mysqlJson, "database");

            // 读取文件配置
            std::string filesJson = jsonStr.substr(jsonStr.find("\"files\""));
            filesJson = filesJson.substr(0, filesJson.find("}") + 1);
            
            csvPath = getValueFromJson(filesJson, "csv_path");
            projectNumber = getValueFromJson(filesJson, "project_number");

            return !host.empty() && !user.empty() && !password.empty() && !database.empty();
        }
        catch (const std::exception& e) {
            std::cerr << "读取配置文件错误: " << e.what() << std::endl;
            return false;
        }
    }

    // 判断连接类型
    std::string determineConnType(const std::string& sourceDevice, const std::string& targetDevice) {
        // 内部线圈判断
        if ((sourceDevice.find("K") == 0 && targetDevice.find("K") == 0) ||
            (sourceDevice.find("KM") == 0 && targetDevice.find("KM") == 0) ||
            (sourceDevice.find("KA") == 0 && targetDevice.find("KA") == 0)) {
            return "内部线圈";
        }
        
        // 内部触点常开判断
        if (sourceDevice.find("NO") != std::string::npos || 
            targetDevice.find("NO") != std::string::npos) {
            return "内部触点常开";
        }
        
        // 内部触点常闭判断
        if (sourceDevice.find("NC") != std::string::npos || 
            targetDevice.find("NC") != std::string::npos) {
            return "内部触点常闭";
        }
        
        // 默认为外部连接
        return "外部连接";
    }

    // 转义字符串
    std::string escapeString(const std::string& str) {
        size_t bufLen = str.length() * 2 + 1;
        std::vector<char> buffer(bufLen);
        unsigned long length = mysql_real_escape_string(conn, buffer.data(), str.c_str(), str.length());
        return std::string(buffer.data(), length);
    }

    // 解析连接信息
    V_Connection parseConnectionInfo(const std::string& connNo, const std::string& source, const std::string& target, const std::string& color) {
        V_Connection conn;
        conn.connNo = connNo;
        conn.source = source;
        conn.target = target;
        conn.color = color;
        
        // 默认电气特性
        conn.voltage = 0.0;
        conn.current = 0.0;
        conn.resistance = 0.0;
        
        // 默认为非电缆
        conn.isCable = false;
        
        // 判断是否为电缆 (通常包含 "Cable" 或 "电缆" 等关键词)
        if (connNo.find("Cable") != std::string::npos || 
            connNo.find("CABLE") != std::string::npos || 
            connNo.find("电缆") != std::string::npos) {
            conn.isCable = true;
        }
        
        // 根据source和target判断连接类型
        conn.connType = determineConnType(source, target);
        
        // 根据颜色和连接类型设置电气特性
        if (color == "RED" || color == "红色") {
            conn.voltage = 220.0;
        } else if (color == "BLUE" || color == "蓝色") {
            conn.voltage = 24.0;
        }
        
        // 对于内部线圈，设置电流
        if (conn.connType == "内部线圈") {
            conn.current = 0.5;
        }
        
        return conn;
    }

public:
    ConnectionImporter(const std::string& table) : tableName(table) {
        conn = mysql_init(NULL);
        if (conn == NULL) {
            std::cerr << "MySQL初始化失败" << std::endl;
            return;
        }

        std::string host, user, password, database;
        if (!loadConfig(host, user, password, database)) {
            std::cerr << "加载配置失败" << std::endl;
            return;
        }

        std::cout << "CSV路径: " << csvPath << std::endl;
        std::cout << "项目编号: " << projectNumber << std::endl;

        if (!mysql_real_connect(conn, host.c_str(), user.c_str(), password.c_str(),
                              database.c_str(), 0, NULL, 0)) {
            std::cerr << "连接数据库失败: " << mysql_error(conn) << std::endl;
            return;
        }

        // 设置字符集
        mysql_set_character_set(conn, "utf8mb4");
        createConnectionTable();
    }

    ~ConnectionImporter() {
        if (conn) {
            mysql_close(conn);
        }
    }

    // 创建连接表
    bool createConnectionTable() {
        std::string dropTable = "DROP TABLE IF EXISTS " + tableName;
        if (mysql_query(conn, dropTable.c_str())) {
            std::cerr << "删除旧表失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        std::string createTable = "CREATE TABLE " + tableName + " ("
            "id INT PRIMARY KEY AUTO_INCREMENT, "
            "connNo VARCHAR(255) NOT NULL, "
            "source VARCHAR(255) NOT NULL, "
            "target VARCHAR(255) NOT NULL, "
            "color VARCHAR(50), "
            "isCable BOOLEAN DEFAULT FALSE, "
            "connType VARCHAR(50), "
            "voltage DOUBLE DEFAULT 0, "
            "current DOUBLE DEFAULT 0, "
            "resistance DOUBLE DEFAULT 0, "
            "UNIQUE KEY conn_unique (source, target), "
            "INDEX idx_source (source), "
            "INDEX idx_target (target), "
            "INDEX idx_conn_type (connType)"
            ") CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci";

        return mysql_query(conn, createTable.c_str()) == 0;
    }

    // 导入CSV数据
    bool importFromCSV() {
        std::ifstream file(csvPath);
        if (!file.is_open()) {
            std::cerr << "无法打开CSV文件: " << csvPath << std::endl;
            return false;
        }

        std::vector<V_Connection> connections;
        std::string line;
        int lineNum = 0;

        // 跳过标题行
        std::getline(file, line);
        std::cout << "跳过标题行: " << line << std::endl;

        // 跳过前两行非设备数据
        std::getline(file, line); // Wire termination processing source
        std::getline(file, line); // Wire termination processing target
        
        while (std::getline(file, line)) {
            lineNum++;
            if (line.empty()) continue;

            std::stringstream ss(line);
            std::string field;
            std::vector<std::string> fields;
            bool inQuotes = false;
            std::string currentField;

            // 解析CSV行，处理引号内的逗号
            for (char c : line) {
                if (c == '"') {
                    inQuotes = !inQuotes;
                } else if (c == ',' && !inQuotes) {
                    fields.push_back(currentField);
                    currentField.clear();
                } else {
                    currentField += c;
                }
            }
            fields.push_back(currentField); // 不要忘记最后一个字段

            // 检查是否有足够的字段
            if (fields.size() >= 10) {
                std::string connNo = fields[0]; // 连接号通常在第一列
                std::string wireColor = fields[9]; // 电线颜色通常在第10列
                
                // 检查源和目标设备是否存在
                if (!fields[7].empty() && !fields[8].empty() && 
                    fields[7].find("=") == 0 && fields[8].find("=") == 0) {
                    V_Connection connection = parseConnectionInfo(
                        connNo, fields[7], fields[8], wireColor);
                    connections.push_back(connection);
                }
            }
        }

        file.close();
        std::cout << "解析完成，共 " << connections.size() << " 个连接" << std::endl;
        return batchInsertConnections(connections);
    }

private:
    // 批量插入连接
    bool batchInsertConnections(const std::vector<V_Connection>& connections) {
        if (mysql_query(conn, "START TRANSACTION")) {
            std::cerr << "开始事务失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        bool success = true;
        for (const auto& connection : connections) {
            std::string query = "INSERT IGNORE INTO " + tableName + 
                " (connNo, source, target, color, isCable, connType, voltage, current, resistance) VALUES ("
                "'" + escapeString(connection.connNo) + "', "
                "'" + escapeString(connection.source) + "', "
                "'" + escapeString(connection.target) + "', "
                "'" + escapeString(connection.color) + "', "
                + std::to_string(connection.isCable) + ", "
                "'" + escapeString(connection.connType) + "', "
                + std::to_string(connection.voltage) + ", "
                + std::to_string(connection.current) + ", "
                + std::to_string(connection.resistance) + ")";

            if (mysql_query(conn, query.c_str()) != 0) {
                std::cerr << "插入失败: " << mysql_error(conn) << std::endl;
                std::cerr << "问题数据: " << connection.source << " -> " << connection.target << std::endl;
                success = false;
                break;
            }
        }

        if (success) {
            if (mysql_query(conn, "COMMIT")) {
                std::cerr << "提交事务失败: " << mysql_error(conn) << std::endl;
                return false;
            }
            std::cout << "成功插入 " << connections.size() << " 条记录" << std::endl;
            return true;
        } else {
            if (mysql_query(conn, "ROLLBACK")) {
                std::cerr << "回滚事务失败: " << mysql_error(conn) << std::endl;
            }
            return false;
        }
    }
};

int main() {
    SetConsoleOutputCP(CP_UTF8);
    
    ConnectionImporter importer("conn_graph");
    if (importer.importFromCSV()) {
        std::cout << "连接数据导入成功" << std::endl;
    } else {
        std::cout << "连接数据导入失败" << std::endl;
    }

    return 0;
}