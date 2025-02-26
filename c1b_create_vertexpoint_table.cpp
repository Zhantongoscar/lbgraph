#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <map>
#include <windows.h>
#include "C:/clib/mysql/include/mysql.h"

// 设备点结构
struct V_DevicePoint {
    std::string FTID;            // 完整设备标识符点ID
    std::string belongtoDevice;  // 属于设备
    std::string Function;        // 功能
    std::string Location;        // 位置
    std::string Device;          // 设备
    std::string Type;            // 点类型
    std::string description;     // 点描述（改为description）
    double voltage;              // 电压
    double current;              // 电流
    double resistance;           // 电阻
    bool isSocket;               // 是否是插座点
    bool isSetPoint;             // 是否具备设定功能
    bool isSensePoint;           // 是否具备感知功能
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

class DevicePointImporter {
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

    // 解析设备点信息
    V_DevicePoint parseDevicePointInfo(const std::string& deviceStr) {
        V_DevicePoint point;
        point.FTID = deviceStr;
        point.belongtoDevice = ""; // 将在后续处理中设置
        
        // 默认电气特性
        point.voltage = 0.0;
        point.current = 0.0;
        point.resistance = 0.0;
        
        // 默认点属性
        point.isSocket = false;
        point.isSetPoint = false;
        point.isSensePoint = false;
        point.description = "";
        point.Type = "Unknown";

        // 解析功能和位置
        size_t equalPos = deviceStr.find("=");
        if (equalPos != std::string::npos) {
            size_t plusPos = deviceStr.find("+", equalPos);
            if (plusPos != std::string::npos) {
                point.Function = deviceStr.substr(equalPos + 1, plusPos - (equalPos + 1));
                
                size_t minusPos = deviceStr.find("-", plusPos);
                if (minusPos != std::string::npos) {
                    point.Location = deviceStr.substr(plusPos + 1, minusPos - (plusPos + 1));
                    
                    // 设备部分需要处理冒号及其后面的部分
                    std::string devicePart = deviceStr.substr(minusPos + 1);
                    size_t colonPos = devicePart.find(":");
                    if (colonPos != std::string::npos) {
                        // 设备部分取冒号前面的内容
                        point.Device = devicePart.substr(0, colonPos);
                        
                        // 提取点的描述 (冒号后的内容)
                        point.description = devicePart.substr(colonPos + 1);
                        
                        // 尝试从描述中提取点的属性
                        if (point.description.find("SET") != std::string::npos) {
                            point.isSetPoint = true;
                        }
                        if (point.description.find("SENSE") != std::string::npos) {
                            point.isSensePoint = true;
                        }
                        if (point.description.find("SOCKET") != std::string::npos) {
                            point.isSocket = true;
                        }
                    } else {
                        point.Device = devicePart;
                    }
                    
                    // 设置所属设备 (设备标识符)
                    point.belongtoDevice = point.Function + "+" + point.Location + "-" + point.Device;
                }
            }
        }

        // 根据设备特征判断类型
        if (point.Device.find("PLC") != std::string::npos) {
            point.Type = "PLC_Point";
        } else if (point.Device.find("X") == 0) {
            point.Type = "Terminal_Point";
        } else if (point.isSetPoint) {
            point.Type = "SetPoint";
        } else if (point.isSensePoint) {
            point.Type = "SensePoint";
        }

        // 通过检查Device前三个字符判断是否是Socket点
        // 根据您的示例，X20开头的设备应该将isSocket设为true
        if (point.Device.length() >= 3) {
            std::string devicePrefix = point.Device.substr(0, 3);
            if (devicePrefix == "X20" || devicePrefix == "X21" || 
                devicePrefix == "X22" || devicePrefix == "X23" || 
                devicePrefix == "X24") {
                point.isSocket = true;
            }
        }

        return point;
    }

    // 转义字符串
    std::string escapeString(const std::string& str) {
        size_t bufLen = str.length() * 2 + 1;
        std::vector<char> buffer(bufLen);
        unsigned long length = mysql_real_escape_string(conn, buffer.data(), str.c_str(), str.length());
        return std::string(buffer.data(), length);
    }

public:
    DevicePointImporter(const std::string& table) : tableName(table) {
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
        createDevicePointTable();
    }

    ~DevicePointImporter() {
        if (conn) {
            mysql_close(conn);
        }
    }

    // 创建设备点表
    bool createDevicePointTable() {
        std::string dropTable = "DROP TABLE IF EXISTS " + tableName;
        if (mysql_query(conn, dropTable.c_str())) {
            std::cerr << "删除旧表失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        std::string createTable = "CREATE TABLE " + tableName + " ("
            "id INT PRIMARY KEY AUTO_INCREMENT, "
            "FTID VARCHAR(255) NOT NULL UNIQUE, "
            "belongtoDevice VARCHAR(255), "
            "Function VARCHAR(255), "
            "Location VARCHAR(255), "
            "Device VARCHAR(255), "
            "Type VARCHAR(50), "
            "description VARCHAR(255), "
            "voltage DOUBLE DEFAULT 0, "
            "current DOUBLE DEFAULT 0, "
            "resistance DOUBLE DEFAULT 0, "
            "isSocket BOOLEAN DEFAULT FALSE, "
            "isSetPoint BOOLEAN DEFAULT FALSE, "
            "isSensePoint BOOLEAN DEFAULT FALSE"
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

        std::vector<V_DevicePoint> devicePoints;
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

            // 处理第8列和第9列的设备点
            if (fields.size() >= 8) {
                // 检查第8列是否以'='开头，确保是设备数据
                if (!fields[7].empty() && fields[7].find("=") == 0) {
                    V_DevicePoint point = parseDevicePointInfo(fields[7]);
                    devicePoints.push_back(point);
                }
                // 检查第9列
                if (fields.size() > 8 && !fields[8].empty() && fields[8].find("=") == 0) {
                    V_DevicePoint point = parseDevicePointInfo(fields[8]);
                    devicePoints.push_back(point);
                }
            }
        }

        file.close();
        std::cout << "解析完成，共 " << devicePoints.size() << " 个设备点" << std::endl;
        return batchInsertDevicePoints(devicePoints);
    }

private:
    // 批量插入设备点
    bool batchInsertDevicePoints(const std::vector<V_DevicePoint>& points) {
        if (mysql_query(conn, "START TRANSACTION")) {
            std::cerr << "开始事务失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        bool success = true;
        for (const auto& point : points) {
            std::string query = "INSERT IGNORE INTO " + tableName + 
                " (FTID, belongtoDevice, Function, Location, Device, Type, description, "
                "voltage, current, resistance, isSocket, isSetPoint, isSensePoint) VALUES ("
                "'" + escapeString(point.FTID) + "', "
                "'" + escapeString(point.belongtoDevice) + "', "
                "'" + escapeString(point.Function) + "', "
                "'" + escapeString(point.Location) + "', "
                "'" + escapeString(point.Device) + "', "
                "'" + escapeString(point.Type) + "', "
                "'" + escapeString(point.description) + "', "
                + std::to_string(point.voltage) + ", "
                + std::to_string(point.current) + ", "
                + std::to_string(point.resistance) + ", "
                + std::to_string(point.isSocket) + ", "
                + std::to_string(point.isSetPoint) + ", "
                + std::to_string(point.isSensePoint) + ")";

            if (mysql_query(conn, query.c_str()) != 0) {
                std::cerr << "插入失败: " << mysql_error(conn) << std::endl;
                std::cerr << "问题数据: " << point.FTID << std::endl;
                success = false;
                break;
            }
        }

        if (success) {
            if (mysql_query(conn, "COMMIT")) {
                std::cerr << "提交事务失败: " << mysql_error(conn) << std::endl;
                return false;
            }
            std::cout << "成功插入 " << points.size() << " 条记录" << std::endl;
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
    
    DevicePointImporter importer("v_device_points");
    if (importer.importFromCSV()) {
        std::cout << "设备点数据导入成功" << std::endl;
    } else {
        std::cout << "设备点数据导入失败" << std::endl;
    }

    return 0;
}