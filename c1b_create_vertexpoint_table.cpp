#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <map>
#include <windows.h>
#include <filesystem>
#include "C:/clib/mysql/include/mysql.h"

namespace fs = std::filesystem;

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

            // 从config.json读取项目编号
            std::string filesJson = jsonStr.substr(jsonStr.find("\"files\""));
            filesJson = filesJson.substr(0, filesJson.find("}") + 1);
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
        point.Type = "";

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
                        
                        // 处理第二个冒号，如果存在，删除第二个冒号及其后面的内容
                        size_t secondColonPos = point.description.find(":");
                        if (secondColonPos != std::string::npos) {
                            // 只保留第一个冒号后到第二个冒号前的内容
                            point.description = point.description.substr(0, secondColonPos);
                        }
                        
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
                    
                    // 设置所属设备 (设备标识符)，添加"="前缀
                    point.belongtoDevice = "=" + point.Function + "+" + point.Location + "-" + point.Device;
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

    // 从目录中获取所有CSV文件
    std::vector<fs::path> getCSVFiles(const std::string& dirPath) {
        std::vector<fs::path> csvFiles;
        try {
            if (!fs::exists(dirPath)) {
                std::cerr << "目录不存在: " << dirPath << std::endl;
                return csvFiles;
            }

            for (const auto& entry : fs::directory_iterator(dirPath)) {
                if (entry.is_regular_file()) {
                    std::string ext = entry.path().extension().string();
                    if (ext == ".csv") {
                        csvFiles.push_back(entry.path());
                    }
                }
            }
        } catch (const std::exception& e) {
            std::cerr << "获取CSV文件列表时出错: " << e.what() << std::endl;
        }
        return csvFiles;
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

    // 让用户选择CSV文件
    bool selectCSVFile() {
        std::string dataDir = "data";
        std::vector<fs::path> csvFiles = getCSVFiles(dataDir);
        
        if (csvFiles.empty()) {
            std::cerr << "在" << dataDir << "目录中未找到CSV文件" << std::endl;
            return false;
        }
        
        std::cout << "请选择要导入的CSV文件:" << std::endl;
        for (size_t i = 0; i < csvFiles.size(); i++) {
            std::cout << (i + 1) << ": " << csvFiles[i].filename().string() << std::endl;
        }
        
        size_t choice;
        std::cout << "请输入选择的序号: ";
        std::cin >> choice;
        
        if (choice < 1 || choice > csvFiles.size()) {
            std::cerr << "无效的选择" << std::endl;
            return false;
        }
        
        csvPath = csvFiles[choice - 1].string();
        std::cout << "已选择文件: " << csvPath << std::endl;
        return true;
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
                // 处理Device (source)字段
                if (!fields[7].empty() && fields[7].find("=") == 0) {
                    // 处理可能包含两个冒号的FTID
                    std::string originalFTID = fields[7];
                    std::string processedFTID = processFTID(originalFTID);
                    
                    // 使用处理后的FTID创建设备点
                    V_DevicePoint point = parseDevicePointInfo(processedFTID);
                    
                    // 保存原始的FTID信息以供参考
                    if (originalFTID != processedFTID) {
                        std::cout << "处理FTID: " << originalFTID << " -> " << processedFTID << std::endl;
                    }
                    
                    devicePoints.push_back(point);
                }
                
                // 处理Device (target)字段
                if (fields.size() > 8 && !fields[8].empty() && fields[8].find("=") == 0) {
                    // 处理可能包含两个冒号的FTID
                    std::string originalFTID = fields[8];
                    std::string processedFTID = processFTID(originalFTID);
                    
                    // 使用处理后的FTID创建设备点
                    V_DevicePoint point = parseDevicePointInfo(processedFTID);
                    
                    // 保存原始的FTID信息以供参考
                    if (originalFTID != processedFTID) {
                        std::cout << "处理FTID: " << originalFTID << " -> " << processedFTID << std::endl;
                    }
                    
                    devicePoints.push_back(point);
                }
            }
        }

        file.close();
        std::cout << "解析完成，共 " << devicePoints.size() << " 个设备点" << std::endl;
        return batchInsertDevicePoints(devicePoints);
    }
    
    // 处理FTID，去除第二个冒号及其后的内容
    std::string processFTID(const std::string& ftid) {
        size_t firstColonPos = ftid.find(":");
        if (firstColonPos != std::string::npos) {
            size_t secondColonPos = ftid.find(":", firstColonPos + 1);
            if (secondColonPos != std::string::npos) {
                // 返回从开头到第二个冒号之前的部分
                return ftid.substr(0, secondColonPos);
            }
        }
        return ftid; // 如果没有找到第二个冒号，返回原始FTID
    }

public:
    // 更新计算字段
    bool updateCalculatedFields() {
        std::cout << "开始更新计算字段..." << std::endl;
        
        // 执行多个更新操作，每个操作针对不同的计算逻辑
        if (!updateVoltageFields()) return false;
        if (!updateTypeFields()) return false;
        // 可以添加更多的更新函数...
        
        std::cout << "计算字段更新完成" << std::endl;
        return true;
    }

private:
    // 更新电压相关字段
    bool updateVoltageFields() {
        std::string query = "UPDATE " + tableName + " SET voltage = 220.0 "
                           "WHERE description LIKE '%220V%' OR description LIKE '%AC220%'";
        if (mysql_query(conn, query.c_str()) != 0) {
            std::cerr << "更新电压字段失败: " << mysql_error(conn) << std::endl;
            return false;
        }
        
        query = "UPDATE " + tableName + " SET voltage = 24.0 "
               "WHERE description LIKE '%24V%' OR description LIKE '%DC24%'";
        if (mysql_query(conn, query.c_str()) != 0) {
            std::cerr << "更新电压字段失败: " << mysql_error(conn) << std::endl;
            return false;
        }
        
        return true;
    }
    
    // 更新类型字段 - 基于其他字段的组合判断
    bool updateTypeFields() {
        std::string query = "UPDATE " + tableName + " SET Type = 'PowerInput' "
                          "WHERE voltage > 0 AND isSocket = TRUE";
        if (mysql_query(conn, query.c_str()) != 0) {
            std::cerr << "更新类型字段失败: " << mysql_error(conn) << std::endl;
            return false;
        }
        
        query = "UPDATE " + tableName + " SET Type = 'ControlPoint' "
               "WHERE isSetPoint = TRUE AND isSensePoint = TRUE";
        if (mysql_query(conn, query.c_str()) != 0) {
            std::cerr << "更新类型字段失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        // 更新线圈类型
        query = "UPDATE " + tableName + " SET Type = 'coil' "
               "WHERE Location LIKE 'K1.%' AND Device LIKE 'Q%' AND description LIKE 'D%'";
        if (mysql_query(conn, query.c_str()) != 0) {
            std::cerr << "更新线圈类型失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        // 更新触点类型
        query = "UPDATE " + tableName + " SET Type = CASE "
               "WHEN description IN ('L1','K1', 'T1') THEN 'MC_NO_1' "
               "WHEN description IN ('L2','K2', 'T2') THEN 'MC_NO_2' "
               "WHEN description IN ('L3','K3', 'T3') THEN 'MC_NO_3' "
               "WHEN description IN ('3.13','13','1','2') THEN 'AC_NO_1' "
               "WHEN description IN ('3.14','14','13','3','4') THEN 'AC_NO_2' "
               "WHEN description IN ('5','6') THEN 'AC_NO_3' "
               "ELSE Type END "
               "WHERE Location LIKE 'K1.%' AND Device LIKE 'Q%'";
        if (mysql_query(conn, query.c_str()) != 0) {
            std::cerr << "更新触点类型失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        // 更新按钮点类型
        query = "UPDATE " + tableName + " SET Type = CASE "
               "WHEN description IN ('1','2','13','14') THEN 'S_NO_1' "
               "WHEN description IN ('.3','.4') THEN 'AC_NO_2' "
               "WHEN description IN ('11','12') THEN 'S_NC_1' "
               "WHEN description IN ('3','4','21','22') THEN 'S_NC_1' "
               "WHEN description IN ('X1','X2') THEN 'LAMP' "
               "ELSE Type END "
               "WHERE Location LIKE 'K1.%' AND Device LIKE 'S%'";
        if (mysql_query(conn, query.c_str()) != 0) {
            std::cerr << "更新按钮点类型失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        // 更新线圈类型 - K设备的线圈
        query = "UPDATE " + tableName + " SET Type = 'coil' "
               "WHERE Location LIKE 'K1.%' AND Device LIKE 'K%' AND description LIKE 'A%'";
        if (mysql_query(conn, query.c_str()) != 0) {
            std::cerr << "更新继电器线圈类型失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        // 更新继电器触点类型
        query = "UPDATE " + tableName + " SET Type = CASE "
               "WHEN description IN ('1','2') THEN 'MC_NO_1' "
               "WHEN description IN ('3','4') THEN 'MC_NO_2' "
               "WHEN description IN ('5','6') THEN 'MC_NO_3' "
               "WHEN description IN ('11') THEN 'AX_COM_1' "
               "WHEN description IN ('12') THEN 'AX_NC_1' "
               "WHEN description IN ('13','14') THEN 'AX_NO_1' "
               "WHEN description IN ('21') THEN 'AX_COM_2' "
               "WHEN description IN ('22') THEN 'AX_NC_2' "
               "WHEN description IN ('23','24') THEN 'AX_NO_2' "
               "WHEN description IN ('31') THEN 'AX_COM_3' "
               "WHEN description IN ('32') THEN 'AX_NC_3' "
               "WHEN description IN ('33','34') THEN 'AX_NO_3' "
               "WHEN description IN ('41') THEN 'AX_COM_4' "
               "WHEN description IN ('42') THEN 'AX_NC_4' "
               "WHEN description IN ('43','44') THEN 'AX_NO_4' "
               "WHEN description IN ('51') THEN 'AX_COM_5' "
               "WHEN description IN ('52') THEN 'AX_NC_5' "
               "WHEN description IN ('53','54') THEN 'AX_NO_5' "
               "WHEN description IN ('61') THEN 'AX_COM_6' "
               "WHEN description IN ('62') THEN 'AX_NC_6' "
               "WHEN description IN ('63','64') THEN 'AX_NO_6' "
               "WHEN description IN ('71') THEN 'AX_COM_7' "
               "WHEN description IN ('72') THEN 'AX_NC_7' "
               "WHEN description IN ('74') THEN 'AX_NO_7' "
               "WHEN description IN ('S11','S21') THEN 'DO' "
               "WHEN description IN ('S12','S22','S34') THEN 'DI' "
               "ELSE Type END "
               "WHERE Location LIKE 'K1.%' AND Device LIKE 'K%'";
        if (mysql_query(conn, query.c_str()) != 0) {
            std::cerr << "更新继电器触点类型失败: " << mysql_error(conn) << std::endl;
            return false;
        }
        
        return true;
    }
    
    // 更多的更新函数可以根据需要添加...

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
    
    // 让用户选择CSV文件
    if (!importer.selectCSVFile()) {
        std::cout << "文件选择失败，程序退出" << std::endl;
        return 1;
    }
    
    // 第一步：导入数据
    if (importer.importFromCSV()) {
        std::cout << "设备点数据导入成功" << std::endl;
        
        // 第二步：更新计算字段
        if (importer.updateCalculatedFields()) {
            std::cout << "计算字段更新成功" << std::endl;
        } else {
            std::cout << "计算字段更新失败" << std::endl;
            // 可以决定是否将此视为整体失败
        }
    } else {
        std::cout << "设备点数据导入失败" << std::endl;
    }

    return 0;
}