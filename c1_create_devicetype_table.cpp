#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <map>
#include <windows.h>
#include "C:/clib/mysql/include/mysql.h"

// 设备节点结构
struct V_Device {
    std::string FDID;          // 完整设备标识符
    std::string Function;      // 功能
    std::string Location;      // 位置
    std::string Device;        // 设备
    bool isInPanel;           // 是否在柜内
    std::string Type;         // 设备类型
    bool isSim;              // 是否为仿真设备
    bool isPLC;              // 是否PLC设备
    bool isTerminal;         // 是否端子设备
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

class DeviceImporter {
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

    // 解析设备信息
    V_Device parseDeviceInfo(const std::string& deviceStr) {
        V_Device device;
        device.FDID = deviceStr;

        // 解析功能和位置
        size_t equalPos = deviceStr.find("=");
        if (equalPos != std::string::npos) {
            size_t plusPos = deviceStr.find("+", equalPos);
            if (plusPos != std::string::npos) {
                device.Function = deviceStr.substr(equalPos + 1, plusPos - (equalPos + 1));
                
                size_t minusPos = deviceStr.find("-", plusPos);
                if (minusPos != std::string::npos) {
                    device.Location = deviceStr.substr(plusPos + 1, minusPos - (plusPos + 1));
                    device.Device = deviceStr.substr(minusPos + 1);
                }
            }
        }

        // 设置默认值
        // 判断Location是否以K1.开头，如果是则isInPanel为true，否则为false
        device.isInPanel = (device.Location.length() >= 3 && device.Location.substr(0, 3) == "K1.");
        device.isSim = false;     // 默认非仿真设备
        device.isPLC = false;     // 默认非PLC设备
        device.isTerminal = false; // 默认非端子设备
        device.Type = "Unknown";   // 默认类型

        // 根据设备特征判断类型
        if (device.Device.find("PLC") != std::string::npos) {
            device.isPLC = true;
            device.Type = "PLC";
        } else if (device.Device.find("X") == 0) {
            device.isTerminal = true;
            device.Type = "Terminal";
        }

        return device;
    }

    // 转义字符串
    std::string escapeString(const std::string& str) {
        size_t bufLen = str.length() * 2 + 1;
        std::vector<char> buffer(bufLen);
        unsigned long length = mysql_real_escape_string(conn, buffer.data(), str.c_str(), str.length());
        return std::string(buffer.data(), length);
    }

public:
    DeviceImporter(const std::string& table) : tableName(table) {
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

        if (!mysql_real_connect(conn, host.c_str(), user.c_str(), password.c_str(),
                              database.c_str(), 0, NULL, 0)) {
            std::cerr << "连接数据库失败" << std::endl;
            return;
        }

        // 设置字符集
        mysql_set_character_set(conn, "utf8mb4");
        createDeviceTable();
    }

    ~DeviceImporter() {
        if (conn) {
            mysql_close(conn);
        }
    }

    // 创建设备表
    bool createDeviceTable() {
        std::string dropTable = "DROP TABLE IF EXISTS " + tableName;
        if (mysql_query(conn, dropTable.c_str())) {
            std::cerr << "删除旧表失败" << std::endl;
            return false;
        }

        std::string createTable = "CREATE TABLE " + tableName + " ("
            "id INT PRIMARY KEY AUTO_INCREMENT, "
            "FDID VARCHAR(255) NOT NULL UNIQUE, "
            "Function VARCHAR(255), "
            "Location VARCHAR(255), "
            "Device VARCHAR(255), "
            "isInPanel BOOLEAN DEFAULT TRUE, "
            "Type VARCHAR(50), "
            "isSim BOOLEAN DEFAULT FALSE, "
            "isPLC BOOLEAN DEFAULT FALSE, "
            "isTerminal BOOLEAN DEFAULT FALSE"
            ") CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci";

        return mysql_query(conn, createTable.c_str()) == 0;
    }

    // 导入CSV数据
    bool importFromCSV() {
        std::ifstream file(csvPath);
        if (!file.is_open()) {
            std::cerr << "无法打开CSV文件" << std::endl;
            return false;
        }

        std::vector<V_Device> devices;
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
            fields.push_back(currentField);

            if (fields.size() >= 8) {
                // 检查第8列是否以'='开头，确保是设备数据
                if (!fields[7].empty() && fields[7].find("=") == 0) {
                    V_Device device = parseDeviceInfo(fields[7]);
                    devices.push_back(device);
                }
                // 检查第9列
                if (fields.size() > 8 && !fields[8].empty() && fields[8].find("=") == 0) {
                    V_Device device = parseDeviceInfo(fields[8]);
                    devices.push_back(device);
                }
            }
        }

        file.close();
        return batchInsertDevices(devices);
    }

private:
    // 批量插入设备
    bool batchInsertDevices(const std::vector<V_Device>& devices) {
        if (mysql_query(conn, "START TRANSACTION")) {
            return false;
        }

        bool success = true;
        for (const auto& device : devices) {
            std::string query = "INSERT IGNORE INTO " + tableName + 
                " (FDID, Function, Location, Device, isInPanel, Type, isSim, isPLC, isTerminal) VALUES ("
                "'" + escapeString(device.FDID) + "', "
                "'" + escapeString(device.Function) + "', "
                "'" + escapeString(device.Location) + "', "
                "'" + escapeString(device.Device) + "', "
                + std::to_string(device.isInPanel) + ", "
                "'" + escapeString(device.Type) + "', "
                + std::to_string(device.isSim) + ", "
                + std::to_string(device.isPLC) + ", "
                + std::to_string(device.isTerminal) + ")";

            if (mysql_query(conn, query.c_str()) != 0) {
                success = false;
                break;
            }
        }

        if (success) {
            return mysql_query(conn, "COMMIT") == 0;
        } else {
            mysql_query(conn, "ROLLBACK");
            return false;
        }
    }
};

int main() {
    SetConsoleOutputCP(CP_UTF8);
    
    DeviceImporter importer("v_devices");
    if (importer.importFromCSV()) {
        std::cout << "设备数据导入成功" << std::endl;
    } else {
        std::cout << "设备数据导入失败" << std::endl;
    }

    return 0;
}