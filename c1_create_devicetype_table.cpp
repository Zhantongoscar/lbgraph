#include <iostream>
#include <fstream>
#include <sstream>
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
    std::string project_number;  // 项目编号
    std::string source;         // 源设备
    std::string target;         // 目标设备
    std::string function;       // = 和 + 之间的内容
    std::string location;       // + 和第一个 - 之间的内容
    std::string device;         // 第一个 - 和第一个: 之间的内容
    std::string terminal_list;  // JSON格式的终端列表
    std::string inner_list;     // JSON格式的内部连接列表
};

class PanelDeviceTable {
private:
    MYSQL* conn;
    std::string tableName;
    std::string csvPath;
    std::string projectNumber;

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

    // 解析设备信息
    void parseDeviceInfo(const std::string& str, DeviceType& device) {
        device.function = extractBetween(str, "=", "+");
        device.location = extractBetween(str, "+", "-");
        
        // 提取设备名称（第一个-和第一个:之间的内容）
        size_t dashPos = str.find("-");
        size_t colonPos = str.find(":");
        if (dashPos != std::string::npos && colonPos != std::string::npos) {
            device.device = str.substr(dashPos + 1, colonPos - dashPos - 1);
            // 提取终端信息（冒号后的所有内容）
            std::string terminal = str.substr(colonPos + 1);
            if (terminal.empty()) {
                device.terminal_list = "{\"terminals\": []}";
            } else {
                device.terminal_list = "{\"terminals\": [\"" + escapeString(terminal) + "\"]}";
            }
        }
    }

public:
    PanelDeviceTable(const std::string& table) : tableName(table) {
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

        // 创建新表
        std::string createTable = "CREATE TABLE " + tableName + " ("
            "id INT PRIMARY KEY AUTO_INCREMENT, "
            "project_number VARCHAR(255) NOT NULL, "
            "source VARCHAR(255) NOT NULL, "
            "target VARCHAR(255) NOT NULL, "
            "function TEXT, "
            "location TEXT, "
            "device VARCHAR(255), "
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
            std::cout << "字段: " << row[0] << ", 类型: " << row[1] << std::endl;
        }
        std::cout << "----------------------------------------\n" << std::endl;
        
        mysql_free_result(result);
    }

    ~PanelDeviceTable() {
        if (conn) {
            mysql_close(conn);
        }
    }

    // 获取CSV路径
    std::string getCsvPath() const {
        return csvPath;
    }

    // 获取项目编号
    std::string getProjectNumber() const {
        return projectNumber;
    }

    // 添加新设备类型
    bool addDeviceType(const DeviceType& device) {
        // Debug output for values
        std::cout << "添加设备类型，值：" << std::endl;
        std::cout << "Project Number: [" << device.project_number << "]" << std::endl;
        std::cout << "Source: [" << device.source << "]" << std::endl;
        std::cout << "Target: [" << device.target << "]" << std::endl;
        std::cout << "Function: [" << device.function << "]" << std::endl;
        std::cout << "Location: [" << device.location << "]" << std::endl;
        std::cout << "Device: [" << device.device << "]" << std::endl;
        std::cout << "Terminal List: [" << device.terminal_list << "]" << std::endl;
        std::cout << "Inner List: [" << device.inner_list << "]" << std::endl;

        // 确保terminal_list是有效的JSON
        std::string terminal_list = device.terminal_list.empty() ? "{\"terminals\": []}" : device.terminal_list;
        // 确保inner_list是有效的JSON
        std::string inner_list = device.inner_list.empty() ? "{}" : device.inner_list;
        
        // 构建SQL查询
        std::string query = "INSERT INTO " + tableName +
            " (project_number, source, target, function, location, device, terminal_list, inner_list) VALUES ("
            "'" + escapeString(device.project_number) + "', "
            "'" + escapeString(device.source) + "', "
            "'" + escapeString(device.target) + "', "
            "'" + escapeString(device.function) + "', "
            "'" + escapeString(device.location) + "', "
            "'" + escapeString(device.device) + "', "
            "'" + escapeString(terminal_list) + "', "
            "'" + escapeString(inner_list) + "'"
            ")";

        // 执行查询并输出详细错误信息
        if (mysql_query(conn, query.c_str()) != 0) {
            std::cerr << "SQL查询失败：" << std::endl;
            std::cerr << "错误码: " << mysql_errno(conn) << std::endl;
            std::cerr << "错误信息: " << mysql_error(conn) << std::endl;
            std::cerr << "执行的SQL: " << query << std::endl;
            return false;
        }
        return true;
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
            std::cout << "项目编号: " << row[1] << std::endl;
            std::cout << "Source: " << row[2] << std::endl;
            std::cout << "Target: " << row[3] << std::endl;
            std::cout << "Function: " << row[4] << std::endl;
            std::cout << "Location: " << row[5] << std::endl;
            std::cout << "Device: " << row[6] << std::endl;
            std::cout << "Terminal List: " << row[7] << std::endl;
            std::cout << "Inner List: " << row[8] << std::endl;
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

    // 批量插入设备类型
    bool batchInsert(const std::vector<DeviceType>& devices) {
        if (devices.empty()) return true;

        std::cout << "开始批量插入..." << std::endl;

        // 开始事务
        if (mysql_query(conn, "START TRANSACTION")) {
            std::cerr << "开始事务失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        bool success = true;
        for (size_t i = 0; i < devices.size(); i++) {
            const auto& device = devices[i];
            
            // Debug output for each record
            std::cout << "\n处理第 " << (i + 1) << " 条记录:" << std::endl;
            std::cout << "Source: " << device.source << std::endl;
            std::cout << "Target: " << device.target << std::endl;
            std::cout << "Function: " << device.function << std::endl;
            std::cout << "Location: " << device.location << std::endl;
            std::cout << "Device: " << device.device << std::endl;
            std::cout << "Terminal List: " << device.terminal_list << std::endl;

            if (!addDeviceType(device)) {
                std::cerr << "\n插入第 " << (i + 1) << " 条记录失败" << std::endl;
                std::cerr << "MySQL错误码: " << mysql_errno(conn) << std::endl;
                std::cerr << "MySQL错误: " << mysql_error(conn) << std::endl;
                success = false;
                break;
            }
            
            if (i > 0 && i % 100 == 0) {
                std::cout << "已成功处理 " << i << " 条记录" << std::endl;
            }
        }

        if (success) {
            std::cout << "提交事务..." << std::endl;
            if (mysql_query(conn, "COMMIT")) {
                std::cerr << "提交事务失败: " << mysql_error(conn) << std::endl;
                std::cerr << "MySQL错误码: " << mysql_errno(conn) << std::endl;
                std::cerr << "MySQL错误: " << mysql_error(conn) << std::endl;
                success = false;
            }
        }

        if (!success) {
            std::cout << "执行回滚..." << std::endl;
            if (mysql_query(conn, "ROLLBACK")) {
                std::cerr << "回滚事务失败: " << mysql_error(conn) << std::endl;
                std::cerr << "MySQL错误码: " << mysql_errno(conn) << std::endl;
                std::cerr << "MySQL错误: " << mysql_error(conn) << std::endl;
            } else {
                std::cerr << "导入失败，已回滚事务" << std::endl;
            }
        }

        return success;
    }

    // 从CSV导入数据
    bool importFromCSV(const std::string& filePath, const std::string& projectNumber) {
        std::cout << "正在从CSV文件导入数据: " << filePath << std::endl;
        std::ifstream file(filePath);
        if (!file.is_open()) {
            std::cerr << "无法打开CSV文件: " << filePath << std::endl;
            return false;
        }

        std::vector<DeviceType> devices;
        std::string line;
        int lineNum = 0;

        // 跳过标题行
        std::getline(file, line);
        std::cout << "标题行: " << line << std::endl;
        
        while (std::getline(file, line)) {
            lineNum++;
            try {
                if (line.empty()) {
                    std::cout << "跳过空行 " << lineNum << std::endl;
                    continue;
                }

                std::stringstream ss(line);
                std::string cell;
                DeviceType device;
                device.project_number = projectNumber;
                
                // 解析CSV行
                if (std::getline(ss, cell, ',')) {  // source
                    device.source = cell;
                }
                if (std::getline(ss, cell, ',')) {  // target
                    device.target = cell;
                    parseDeviceInfo(cell, device);
                }

                // 初始化空的inner_list
                device.inner_list = "{}";
                
                devices.push_back(device);
                
                if (lineNum % 100 == 0) {
                    std::cout << "已读取 " << lineNum << " 行..." << std::endl;
                }
            }
            catch (const std::exception& e) {
                std::cerr << "处理第 " << lineNum << " 行时发生错误: " << e.what() << std::endl;
                std::cerr << "行内容: " << line << std::endl;
                continue;
            }
        }

        file.close();
        std::cout << "读取了 " << devices.size() << " 条记录，开始导入..." << std::endl;
        
        if (devices.empty()) {
            std::cerr << "没有有效的记录可导入" << std::endl;
            return false;
        }

        return batchInsert(devices);
    }
};

int main() {
    // 设置控制台输出为UTF-8
    SetConsoleOutputCP(CP_UTF8);
    // 禁用stdout缓冲
    setbuf(stdout, NULL);

    std::cout << "程序开始执行..." << std::endl;
    PanelDeviceTable table("panel_device_types");

    // 从CSV导入数据，使用配置文件中的路径和项目编号
    std::cout << "\n尝试从CSV导入数据..." << std::endl;
    if (table.importFromCSV(table.getCsvPath(), table.getProjectNumber())) {
        std::cout << "数据导入成功" << std::endl;
    } else {
        std::cout << "数据导入失败" << std::endl;
    }

    // 显示导入后的设备列表
    std::cout << "\n导入后的设备列表：" << std::endl;
    table.displayAll();

    std::cout << "\n程序执行完成" << std::endl;
    return 0;
}