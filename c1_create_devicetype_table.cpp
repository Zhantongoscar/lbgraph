#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <map>
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
    std::string name;
    std::string description;
    std::string manufacturer;
    std::string model;
};

class DeviceTypeTable {
private:
    MYSQL* conn;
    std::string tableName;

    // 从config.json读取MySQL配置
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
            std::cout << "读取配置文件内容..." << std::endl;
            while (std::getline(configFile, line)) {
                jsonStr += line;
            }
            std::cout << "配置文件内容: " << jsonStr << std::endl;

            std::cout << "解析MySQL配置..." << std::endl;
            // 从mysql节点下获取配置
            std::string mysqlJson = jsonStr.substr(jsonStr.find("\"mysql\""));
            mysqlJson = mysqlJson.substr(0, mysqlJson.find("}") + 1);
            
            host = getValueFromJson(mysqlJson, "host");
            user = getValueFromJson(mysqlJson, "user");
            password = getValueFromJson(mysqlJson, "password");
            database = getValueFromJson(mysqlJson, "database");

            std::cout << "解析结果:" << std::endl;
            std::cout << "Host: " << host << std::endl;
            std::cout << "User: " << user << std::endl;
            std::cout << "Database: " << database << std::endl;

            bool isValid = !host.empty() && !user.empty() && !password.empty() && !database.empty();
            if (!isValid) {
                std::cerr << "配置不完整" << std::endl;
            }
            return isValid;
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

public:
    DeviceTypeTable(const std::string& table) : tableName(table) {
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

        // 创建表（如果不存在）
        std::string createTable = "CREATE TABLE IF NOT EXISTS " + tableName + " ("
            "id INT PRIMARY KEY AUTO_INCREMENT, "
            "name VARCHAR(255), "
            "description TEXT, "
            "manufacturer VARCHAR(255), "
            "model VARCHAR(255)) "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci";
        
        if (mysql_query(conn, createTable.c_str())) {
            std::cerr << "创建表失败: " << mysql_error(conn) << std::endl;
            return;
        }
    }

    ~DeviceTypeTable() {
        if (conn) {
            mysql_close(conn);
        }
    }

    // 添加新设备类型
    bool addDeviceType(const std::string& name, const std::string& description,
                      const std::string& manufacturer, const std::string& model) {
        std::string escapedName = escapeString(name);
        std::string escapedDesc = escapeString(description);
        std::string escapedMfr = escapeString(manufacturer);
        std::string escapedModel = escapeString(model);
        
        std::string query = "INSERT INTO " + tableName + 
            " (name, description, manufacturer, model) VALUES ('" +
            escapedName + "', '" +
            escapedDesc + "', '" +
            escapedMfr + "', '" +
            escapedModel + "')";

        return mysql_query(conn, query.c_str()) == 0;
    }

    // 显示所有设备类型
    void displayAll() {
        std::string query = "SELECT * FROM " + tableName;
        if (mysql_query(conn, query.c_str())) {
            std::cerr << "查询失败: " << mysql_error(conn) << std::endl;
            return;
        }

        MYSQL_RES* result = mysql_store_result(conn);
        if (result == NULL) {
            std::cerr << "获取结果失败: " << mysql_error(conn) << std::endl;
            return;
        }

        std::cout << "\n设备类型列表：" << std::endl;
        std::cout << "----------------------------------------" << std::endl;

        MYSQL_ROW row;
        while ((row = mysql_fetch_row(result))) {
            std::cout << "ID: " << row[0] << std::endl;
            std::cout << "名称: " << row[1] << std::endl;
            std::cout << "描述: " << row[2] << std::endl;
            std::cout << "制造商: " << row[3] << std::endl;
            std::cout << "型号: " << row[4] << std::endl;
            std::cout << "----------------------------------------" << std::endl;
        }

        mysql_free_result(result);
    }

    // 更新设备类型
    bool updateDeviceType(int id, const std::string& name, const std::string& description,
                         const std::string& manufacturer, const std::string& model) {
        std::string escapedName = escapeString(name);
        std::string escapedDesc = escapeString(description);
        std::string escapedMfr = escapeString(manufacturer);
        std::string escapedModel = escapeString(model);
        
        std::string query = "UPDATE " + tableName + " SET "
            "name='" + escapedName + "', "
            "description='" + escapedDesc + "', "
            "manufacturer='" + escapedMfr + "', "
            "model='" + escapedModel + "' "
            "WHERE id=" + std::to_string(id);

        return mysql_query(conn, query.c_str()) == 0;
    }

    // 删除设备类型
    bool deleteDeviceType(int id) {
        std::string query = "DELETE FROM " + tableName + " WHERE id=" + std::to_string(id);
        return mysql_query(conn, query.c_str()) == 0;
    }
};

int main() {
    // 设置控制台输出为UTF-8
    SetConsoleOutputCP(CP_UTF8);
    // 禁用stdout缓冲
    setbuf(stdout, NULL);

    std::cout << "程序开始执行..." << std::endl;
    DeviceTypeTable table("device_types");

    std::cout << "正在添加测试设备..." << std::endl;
    if (table.addDeviceType("继电器", "控制用继电器", "莱宝", "LB-001")) {
        std::cout << "成功添加继电器" << std::endl;
    }
    if (table.addDeviceType("传感器", "温度传感器", "莱宝", "LB-002")) {
        std::cout << "成功添加传感器" << std::endl;
    }

    std::cout << "\n显示所有设备信息：" << std::endl;
    table.displayAll();

    std::cout << "\n正在更新设备信息..." << std::endl;
    if (table.updateDeviceType(1, "高压继电器", "高压控制继电器", "莱宝", "LB-001-HV")) {
        std::cout << "成功更新设备信息" << std::endl;
    }

    std::cout << "\n更新后的设备列表：" << std::endl;
    table.displayAll();

    std::cout << "\n程序执行完成" << std::endl;

    return 0;
}