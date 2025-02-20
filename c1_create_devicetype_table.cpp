#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <map>
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

    // 从字符串中提取设备标识符和端口号
    std::pair<std::string, std::string> extractDeviceAndPort(const std::string& str) {
        // 去除开头的等号
        size_t startPos = (str[0] == '=') ? 1 : 0;
        std::string deviceStr = str.substr(startPos);
        
        // 查找冒号位置
        size_t colonPos = deviceStr.find(":");
        if (colonPos == std::string::npos) {
            return std::make_pair(deviceStr, "1"); // 如果没有冒号，返回默认端口号"1"
        }

        return std::make_pair(
            deviceStr.substr(0, colonPos),        // 设备标识符（不包含开头的=）
            deviceStr.substr(colonPos + 1)        // 端口号
        );
    }

    // 解析设备信息
    void parseDeviceInfo(const std::string& str, DeviceType& device) {
        // 提取设备标识符和端口号
        auto [deviceId, port] = extractDeviceAndPort(str);
        device.device = deviceId;
        
        // 提取 function 和 location（如果需要的话）
        if (deviceId.find("+") != std::string::npos) {
            size_t plusPos = deviceId.find("+");
            device.function = deviceId.substr(0, plusPos);
            
            size_t nextMinusPos = deviceId.find("-", plusPos);
            if (nextMinusPos != std::string::npos) {
                device.location = deviceId.substr(plusPos + 1, nextMinusPos - (plusPos + 1));
            }
        }

        // 创建只包含端口号的 terminal_list
        device.terminal_list = "{\"terminals\": [{\"port\": \"" + port + "\"}]}";
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

        // 解析现有的 terminal_list
        std::vector<std::string> ports;
        size_t pos = 0;
        while ((pos = existingTerminalList.find("\"port\": \"", pos)) != std::string::npos) {
            pos += 9; // 跳过 "port": "
            size_t endPos = existingTerminalList.find("\"", pos);
            if (endPos != std::string::npos) {
                std::string port = existingTerminalList.substr(pos, endPos - pos);
                // 使用 find_if 和 lambda 函数来检查端口是否存在
                if (std::find_if(ports.begin(), ports.end(),
                    [&port](const std::string& p) { return p == port; }) == ports.end()) {
                    ports.push_back(port);
                }
            }
        }

        // 检查新端口是否已存在
        if (std::find_if(ports.begin(), ports.end(),
            [&newPort](const std::string& p) { return p == newPort; }) == ports.end()) {
            ports.push_back(newPort);
        }

        // 构建新的 terminal_list
        std::string newTerminalList = "{\"terminals\": [";
        for (size_t i = 0; i < ports.size(); ++i) {
            if (i > 0) newTerminalList += ",";
            newTerminalList += "{\"port\": \"" + ports[i] + "\"}";
        }
        newTerminalList += "]}";

        // 更新数据库
        std::string query = "UPDATE " + tableName + 
                          " SET terminal_list = '" + escapeString(newTerminalList) + "'" +
                          " WHERE device = '" + escapeString(deviceId) + "'";

        return mysql_query(conn, query.c_str()) == 0;
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

    // 添加新设备类型，调整字段顺序和处理 terminal_list
    bool addDeviceType(const DeviceType& device) {
        // 提取端口号
        size_t pos = device.terminal_list.find("\"port\": \"");
        size_t endPos = device.terminal_list.find("\"}", pos);
        std::string port = device.terminal_list.substr(pos + 9, endPos - (pos + 9));

        // 检查设备是否已存在
        std::string existingTerminalList;
        if (deviceExists(device.device, existingTerminalList)) {
            // 设备存在，更新端口列表
            return updateDeviceTerminals(device.device, port);
        }

        // 设备不存在，添加新设备
        std::string query = "INSERT INTO " + tableName +
            " (device, project_number, type, function, location, terminal_list, inner_list) VALUES ("
            "'" + escapeString(device.device) + "', "
            "'" + escapeString(device.project_number) + "', "
            "'" + escapeString(device.type) + "', "
            "'" + escapeString(device.function) + "', "
            "'" + escapeString(device.location) + "', "
            "'" + escapeString(device.terminal_list) + "', "
            "'" + escapeString(device.inner_list.empty() ? "{}" : device.inner_list) + "'"
            ")";

        return mysql_query(conn, query.c_str()) == 0;
    }

    // 显示所有设备类型的简化输出
    void displayAll() {
        std::string query = "SELECT * FROM " + tableName;
        if (mysql_query(conn, query.c_str())) {
            return;
        }

        MYSQL_RES* result = mysql_store_result(conn);
        if (result == NULL) {
            std::cerr << "获取结果失败: " << mysql_error(conn) << std::endl;
            return;
        }

        std::cout << "\n设备端口列表：" << std::endl;
        std::cout << "----------------------------------------" << std::endl;

        MYSQL_ROW row;
        while ((row = mysql_fetch_row(result))) {
            std::cout << "Device: " << row[1] << std::endl;
            std::cout << "Ports: " << row[5] << std::endl;  // terminal_list
            std::cout << "----------------------------------------" << std::endl;
        }

        mysql_free_result(result);
    }

    // 显示简化的设备端口列表
    void displayDevicePorts() {
        std::string query = "SELECT device, type, terminal_list FROM " + tableName + " ORDER BY device";
        if (mysql_query(conn, query.c_str())) {
            std::cerr << "查询失败: " << mysql_error(conn) << std::endl;
            return;
        }

        MYSQL_RES* result = mysql_store_result(conn);
        if (result == NULL) {
            std::cerr << "获取结果失败: " << mysql_error(conn) << std::endl;
            return;
        }

        std::cout << "\n设备端口列表：" << std::endl;
        std::cout << "----------------------------------------" << std::endl;

        MYSQL_ROW row;
        while ((row = mysql_fetch_row(result))) {
            std::string device = row[0];
            std::string type = row[1] ? row[1] : "";
            std::string terminalList = row[2];
            
            // 提取所有端口
            std::vector<std::string> ports;
            size_t pos = 0;
            while ((pos = terminalList.find("\"port\": \"", pos)) != std::string::npos) {
                pos += 9;
                size_t endPos = terminalList.find("\"", pos);
                if (endPos != std::string::npos) {
                    ports.push_back(terminalList.substr(pos, endPos - pos));
                }
            }
            
            // 输出设备、类型和端口列表
            std::cout << device;
            if (!type.empty()) {
                std::cout << " [Type: " << type << "]";
            }
            std::cout << ": ";
            
            for (size_t i = 0; i < ports.size(); ++i) {
                if (i > 0) std::cout << ", ";
                std::cout << ports[i];
            }
            std::cout << std::endl;
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
            std::cout << "Device: " << device.device << std::endl;
            std::cout << "Function: " << device.function << std::endl;
            std::cout << "Location: " << device.location << std::endl;
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
        int processedLines = 0;
        const int MAX_LINES = 2000; // 限制处理前30行

        // 跳过标题行
        std::getline(file, line);
        std::cout << "标题行: " << line << std::endl;
        
        while (std::getline(file, line) && processedLines < MAX_LINES) {
            lineNum++;
            try {
                if (line.empty()) {
                    std::cout << "跳过空行 " << lineNum << std::endl;
                    continue;
                }

                std::vector<std::string> fields;
                std::string field;
                bool inQuotes = false;
                std::stringstream fieldValue;

                // 手动解析CSV字段，处理引号内的逗号和换行符
                for (char c : line) {
                    if (c == '\"') {
                        inQuotes = !inQuotes;
                    } else if (c == ',' && !inQuotes) {
                        // 移除前后的空格
                        std::string trimmed = fieldValue.str();
                        while (!trimmed.empty() && isspace(trimmed.front())) trimmed.erase(0, 1);
                        while (!trimmed.empty() && isspace(trimmed.back())) trimmed.pop_back();
                        fields.push_back(trimmed);
                        fieldValue.str("");
                        fieldValue.clear();
                    } else {
                        fieldValue << c;
                    }
                }
                // 添加最后一个字段（同样去除空格）
                std::string trimmed = fieldValue.str();
                while (!trimmed.empty() && isspace(trimmed.front())) trimmed.erase(0, 1);
                while (!trimmed.empty() && isspace(trimmed.back())) trimmed.pop_back();
                fields.push_back(trimmed);

                // 输出解析后的字段用于调试
                std::cout << "\n第 " << lineNum << " 行解析结果:" << std::endl;
                for (size_t i = 0; i < fields.size(); ++i) {
                    std::cout << "字段 " << i << ": [" << fields[i] << "]" << std::endl;
                }

                if (fields.size() < 8) {
                    std::cout << "跳过无效行 " << lineNum << ": 字段数不足" << std::endl;
                    continue;
                }

                std::string source = fields[7];
                std::string target = fields[8];

                // 处理source设备
                if (!source.empty()) {
                    DeviceType device;
                    device.project_number = projectNumber;
                    parseDeviceInfo(source, device);
                    if (!device.device.empty()) {
                        devices.push_back(device);
                    }
                }

                // 处理target设备
                if (!target.empty()) {
                    DeviceType device;
                    device.project_number = projectNumber;
                    parseDeviceInfo(target, device);
                    if (!device.device.empty()) {
                        devices.push_back(device);
                    }
                }

                processedLines++;
                if (processedLines % 10 == 0) {
                    std::cout << "已处理 " << processedLines << " 行数据..." << std::endl;
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
    PanelDeviceTable table("panel_device_inner");

    // 从CSV导入数据，使用配置文件中的路径和项目编号
    std::cout << "\n尝试从CSV导入数据..." << std::endl;
    if (table.importFromCSV(table.getCsvPath(), table.getProjectNumber())) {
        std::cout << "数据导入成功" << std::endl;
        // 使用新的显示函数
        table.displayDevicePorts();
    } else {
        std::cout << "数据导入失败" << std::endl;
    }

    std::cout << "\n程序执行完成" << std::endl;
    return 0;
}