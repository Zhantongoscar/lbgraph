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

// CSV行数据结构
struct CSVRow {
    std::string source;    // 源
    std::string target;    // 目标
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

class CSVImporter {
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
    CSVImporter(const std::string& table) : tableName(table) {
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
        createCSVTable();
    }

    ~CSVImporter() {
        if (conn) {
            mysql_close(conn);
        }
    }

    // 创建CSV表
    bool createCSVTable() {
        std::string dropTable = "DROP TABLE IF EXISTS " + tableName;
        if (mysql_query(conn, dropTable.c_str())) {
            std::cerr << "删除旧表失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        std::string createTable = "CREATE TABLE " + tableName + " ("
            "id INT PRIMARY KEY AUTO_INCREMENT, "
            "source VARCHAR(255) NOT NULL, "
            "target VARCHAR(255) NOT NULL"
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

        std::vector<CSVRow> rows;
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

            // 从第8列和第9列提取source和target
            if (fields.size() >= 8) {
                CSVRow row;
                row.source = fields[7];
                if (fields.size() > 8) {
                    row.target = fields[8];
                }
                rows.push_back(row);
            }
        }

        file.close();
        return batchInsertRows(rows);
    }

private:
    // 批量插入数据
    bool batchInsertRows(const std::vector<CSVRow>& rows) {
        if (mysql_query(conn, "START TRANSACTION")) {
            std::cerr << "开始事务失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        bool success = true;
        for (const auto& row : rows) {
            if (!row.source.empty() && !row.target.empty()) {
                std::string query = "INSERT INTO " + tableName + 
                    " (source, target) VALUES ("
                    "'" + escapeString(row.source) + "', "
                    "'" + escapeString(row.target) + "')";

                if (mysql_query(conn, query.c_str()) != 0) {
                    std::cerr << "插入失败: " << mysql_error(conn) << std::endl;
                    success = false;
                    break;
                }
            }
        }

        if (success) {
            if (mysql_query(conn, "COMMIT")) {
                std::cerr << "提交事务失败: " << mysql_error(conn) << std::endl;
                return false;
            }
            std::cout << "成功插入 " << rows.size() << " 条记录" << std::endl;
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
    
    CSVImporter importer("v_csv_raw");

    // 让用户选择CSV文件
    if (!importer.selectCSVFile()) {
        std::cout << "文件选择失败，程序退出" << std::endl;
        return 1;
    }
    
    if (importer.importFromCSV()) {
        std::cout << "数据导入成功" << std::endl;
    } else {
        std::cout << "数据导入失败" << std::endl;
    }

    return 0;
}