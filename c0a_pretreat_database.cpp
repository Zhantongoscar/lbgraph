#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <map>
#include <windows.h>
#include <filesystem>
#include "C:/clib/mysql/include/mysql.h"
#include "include/nlohmann/json.hpp"

using json = nlohmann::json;
namespace fs = std::filesystem;

// 数据库配置结构
struct DbConfig {
    std::string host;
    std::string user;
    std::string password;
    std::string database;

    static DbConfig loadFromJson(const std::string& configPath) {
        std::ifstream f(configPath);
        if (!f.is_open()) {
            throw std::runtime_error("无法打开配置文件: " + configPath);
        }

        json config = json::parse(f);
        DbConfig dbConfig;
        
        try {
            dbConfig.host = config["mysql"]["host"];
            dbConfig.user = config["mysql"]["user"];
            dbConfig.password = config["mysql"]["password"];
            dbConfig.database = config["mysql"]["database"];
        } catch (const json::exception& e) {
            throw std::runtime_error("解析数据库配置失败: " + std::string(e.what()));
        }

        return dbConfig;
    }
};

// CSV行数据结构
struct CSVRow {
    std::string cnumber;     // 连续编号 Consecutive number
    
    // 源端数据
    std::string s_raw;        // 原始源数据
    std::string s_ftid;       // 源完整标识符
    std::string s_function;   // 源功能
    std::string s_location;   // 源位置
    std::string s_device;     // 源设备
    std::string s_terminal;   // 源端子

    // 目标端数据
    std::string t_raw;        // 原始目标数据
    std::string t_ftid;       // 目标完整标识符
    std::string t_function;   // 目标功能
    std::string t_location;   // 目标位置
    std::string t_device;     // 目标设备
    std::string t_terminal;   // 目标端子
};

// 解析FTID并提取各个部分
void parseFTID(const std::string& raw, std::string& ftid, std::string& function, 
               std::string& location, std::string& device, std::string& terminal) {
    ftid = raw;
    function = "";
    location = "";
    device = "";
    terminal = "";
    
    // 查找等号位置（功能分隔符）
    size_t equalPos = raw.find("=");
    if (equalPos != std::string::npos) {
        // 提取功能部分
        size_t plusPos = raw.find("+", equalPos);
        if (plusPos != std::string::npos) {
            function = raw.substr(equalPos + 1, plusPos - (equalPos + 1));
            
            // 提取位置和设备部分
            size_t minusPos = raw.find("-", plusPos);
            if (minusPos != std::string::npos) {
                location = raw.substr(plusPos + 1, minusPos - (plusPos + 1));
                
                // 处理设备和端子部分
                std::string devicePart = raw.substr(minusPos + 1);
                size_t colonPos = devicePart.find(":");
                if (colonPos != std::string::npos) {
                    device = devicePart.substr(0, colonPos);
                    terminal = devicePart.substr(colonPos + 1);
                    
                    // 处理第二个冒号
                    size_t secondColonPos = terminal.find(":");
                    if (secondColonPos != std::string::npos) {
                        terminal = terminal.substr(0, secondColonPos);
                    }
                } else {
                    device = devicePart;
                    terminal = "";
                }
            }
        }
    }
}

class CSVImporter {
private:
    MYSQL* conn;
    std::string tableName;
    std::string csvPath;
    DbConfig dbConfig;

    // 转义 SQL 字符串
    std::string escapeString(const std::string& str) {
        char* escaped = new char[str.length() * 2 + 1];
        mysql_real_escape_string(conn, escaped, str.c_str(), str.length());
        std::string result(escaped);
        delete[] escaped;
        return result;
    }

public:
    CSVImporter(const std::string& table, const DbConfig& config) 
        : tableName(table), dbConfig(config) {
        std::cout << "初始化 MySQL..." << std::endl;
        
        conn = mysql_init(nullptr);
        if (conn == nullptr) {
            throw std::runtime_error("MySQL 初始化失败: " + std::string(mysql_error(nullptr)));
        }

        std::cout << "连接到数据库..." << std::endl;
        std::cout << "主机: " << dbConfig.host << std::endl;
        std::cout << "用户: " << dbConfig.user << std::endl;
        std::cout << "数据库: " << dbConfig.database << std::endl;

        if (!mysql_real_connect(conn, dbConfig.host.c_str(), 
                              dbConfig.user.c_str(), 
                              dbConfig.password.c_str(),
                              dbConfig.database.c_str(), 
                              3306, nullptr, 0)) {
            std::string error = mysql_error(conn);
            mysql_close(conn);
            throw std::runtime_error("连接数据库失败: " + error);
        }

        std::cout << "设置字符集为 utf8mb4..." << std::endl;
        if (mysql_set_character_set(conn, "utf8mb4")) {
            std::string error = mysql_error(conn);
            mysql_close(conn);
            throw std::runtime_error("设置字符集失败: " + error);
        }

        std::cout << "数据库连接成功！" << std::endl;
    }

    ~CSVImporter() {
        if (conn != nullptr) {
            mysql_close(conn);
            std::cout << "关闭数据库连接" << std::endl;
        }
    }

    // 选择CSV文件
    bool selectCSVFile() {
        std::cout << "打开文件选择对话框..." << std::endl;
        
        OPENFILENAMEA ofn;
        char szFile[260] = { 0 };
        
        ZeroMemory(&ofn, sizeof(ofn));
        ofn.lStructSize = sizeof(ofn);
        ofn.hwndOwner = NULL;
        ofn.lpstrFile = szFile;
        ofn.nMaxFile = sizeof(szFile);
        ofn.lpstrFilter = "CSV Files\0*.csv\0All Files\0*.*\0";
        ofn.nFilterIndex = 1;
        ofn.lpstrFileTitle = NULL;
        ofn.nMaxFileTitle = 0;
        ofn.lpstrInitialDir = NULL;
        ofn.Flags = OFN_PATHMUSTEXIST | OFN_FILEMUSTEXIST;

        if (GetOpenFileNameA(&ofn)) {
            csvPath = ofn.lpstrFile;
            std::cout << "已选择文件: " << csvPath << std::endl;
            return true;
        }
        std::cout << "未选择文件或取消选择" << std::endl;
        return false;
    }

    // 创建CSV表
    bool createCSVTable() {
        std::cout << "正在创建数据表 " << tableName << "..." << std::endl;
        
        std::string dropTable = "DROP TABLE IF EXISTS " + tableName;
        if (mysql_query(conn, dropTable.c_str())) {
            std::cerr << "删除旧表失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        std::string createTable = "CREATE TABLE " + tableName + " ("
            "id INT PRIMARY KEY AUTO_INCREMENT, "
            "cnumber VARCHAR(50), "
            "s_raw VARCHAR(255) NOT NULL, "
            "s_ftid VARCHAR(255), "
            "s_function VARCHAR(255), "
            "s_location VARCHAR(255), "
            "s_device VARCHAR(255), "
            "s_terminal VARCHAR(255), "
            "t_raw VARCHAR(255) NOT NULL, "
            "t_ftid VARCHAR(255), "
            "t_function VARCHAR(255), "
            "t_location VARCHAR(255), "
            "t_device VARCHAR(255), "
            "t_terminal VARCHAR(255)"
            ") CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci";

        if (mysql_query(conn, createTable.c_str())) {
            std::cerr << "创建表失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        std::cout << "数据表创建成功" << std::endl;
        return true;
    }

    // 导入CSV数据
    bool importFromCSV() {
        if (!createCSVTable()) {
            std::cerr << "创建表失败" << std::endl;
            return false;
        }

        std::cout << "打开CSV文件: " << csvPath << std::endl;
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

            // 确保有足够的字段
            if (fields.size() >= 9) {
                CSVRow row;
                
                // 提取 Consecutive number (连续编号)
                row.cnumber = fields[0];
                
                // 处理源数据
                row.s_raw = fields[7];
                if (!row.s_raw.empty()) {
                    parseFTID(row.s_raw, row.s_ftid, row.s_function, 
                             row.s_location, row.s_device, row.s_terminal);
                }

                // 处理目标数据
                row.t_raw = fields[8];
                if (!row.t_raw.empty()) {
                    parseFTID(row.t_raw, row.t_ftid, row.t_function, 
                             row.t_location, row.t_device, row.t_terminal);
                }
                rows.push_back(row);
            }
        }

        file.close();
        std::cout << "CSV文件解析完成，开始导入数据..." << std::endl;
        return batchInsertRows(rows);
    }


     // 新增方法：执行数据格式处理





     


     




     bool formatData() {
    std::cout << "执行数据格式化..." << std::endl;

    // 开始事务
    if (mysql_query(conn, "START TRANSACTION")) {
        std::cerr << "开始事务失败: " << mysql_error(conn) << std::endl;
        return false;
    }

    // --- 1. 处理括号和冒号的情况 ---
    std::string query_s_bracket = R"(
        UPDATE v_csv_raw
        SET s_ftid = CONCAT(
            SUBSTRING(s_raw, 1, LOCATE(':', s_raw) - 1),
            ':',
            TRIM(LEADING '-' FROM 
                SUBSTRING(
                    s_raw, 
                    LOCATE('(', s_raw) + 1, 
                    LOCATE(')', s_raw) - LOCATE('(', s_raw) - 1
                )
            )
        )
        WHERE s_raw LIKE '%(%):%'
    )";

    if (mysql_query(conn, query_s_bracket.c_str())) {
        std::cerr << "更新 s_ftid (括号逻辑) 失败: " << mysql_error(conn) << std::endl;
        mysql_query(conn, "ROLLBACK");
        return false;
    }

    std::string query_t_bracket = R"(
        UPDATE v_csv_raw
        SET t_ftid = CONCAT(
            SUBSTRING(t_raw, 1, LOCATE(':', t_raw) - 1),
            ':',
            TRIM(LEADING '-' FROM 
                SUBSTRING(
                    t_raw, 
                    LOCATE('(', t_raw) + 1, 
                    LOCATE(')', t_raw) - LOCATE('(', t_raw) - 1
                )
            )
        )
        WHERE t_raw LIKE '%(%):%'
    )";

    if (mysql_query(conn, query_t_bracket.c_str())) {
        std::cerr << "更新 t_ftid (括号逻辑) 失败: " << mysql_error(conn) << std::endl;
        mysql_query(conn, "ROLLBACK");
        return false;
    }

    // --- 2. 处理包含 "-A" 的情况 ---
    std::string query_s_A = R"(
        UPDATE v_csv_raw
        SET s_ftid = CONCAT(
            SUBSTRING_INDEX(s_raw, ':', 1),
            '-',
            SUBSTRING(s_raw, LOCATE(':', s_raw) + 1)
        )
        WHERE s_raw LIKE '%-A%'
    )";

    if (mysql_query(conn, query_s_A.c_str())) {
        std::cerr << "更新 s_ftid (-A) 失败: " << mysql_error(conn) << std::endl;
        mysql_query(conn, "ROLLBACK");
        return false;
    }

    std::string query_t_A = R"(
        UPDATE v_csv_raw
        SET t_ftid = CONCAT(
            SUBSTRING_INDEX(t_raw, ':', 1),
            '-',
            SUBSTRING(t_raw, LOCATE(':', t_raw) + 1)
        )
        WHERE t_raw LIKE '%-A%'
    )";

    if (mysql_query(conn, query_t_A.c_str())) {
        std::cerr << "更新 t_ftid (-A) 失败: " << mysql_error(conn) << std::endl;
        mysql_query(conn, "ROLLBACK");
        return false;
    }

    // --- 3. 处理包含 "-X" 和多个冒号的情况 ---
    std::string query_s_X = R"(
        UPDATE v_csv_raw
        SET s_ftid = SUBSTRING_INDEX(s_raw, ':', 2)
        WHERE s_raw LIKE '%-X%:%:%'
    )";

    if (mysql_query(conn, query_s_X.c_str())) {
        std::cerr << "更新 s_ftid (-X) 失败: " << mysql_error(conn) << std::endl;
        mysql_query(conn, "ROLLBACK");
        return false;
    }

    std::string query_t_X = R"(
        UPDATE v_csv_raw
        SET t_ftid = SUBSTRING_INDEX(t_raw, ':', 2)
        WHERE t_raw LIKE '%-X%:%:%'
    )";

    if (mysql_query(conn, query_t_X.c_str())) {
        std::cerr << "更新 t_ftid (-X) 失败: " << mysql_error(conn) << std::endl;
        mysql_query(conn, "ROLLBACK");
        return false;
    }

    // --- 4. 处理 "-D/-E/-G/-M/-U" 的情况 ---
    std::string query_s_DEGMU = R"(
        UPDATE v_csv_raw
        SET s_ftid = CONCAT(
            SUBSTRING_INDEX(s_raw, ':', 1),
            '-',
            SUBSTRING(s_raw, LOCATE(':', s_raw) + 1)
        )
        WHERE s_raw LIKE '%-D%' OR s_raw LIKE '%-E%' OR 
              s_raw LIKE '%-G%' OR s_raw LIKE '%-M%' OR 
              s_raw LIKE '%-U%'
    )";

    if (mysql_query(conn, query_s_DEGMU.c_str())) {
        std::cerr << "更新 s_ftid (-DEGMU) 失败: " << mysql_error(conn) << std::endl;
        mysql_query(conn, "ROLLBACK");
        return false;
    }

    std::string query_t_DEGMU = R"(
        UPDATE v_csv_raw
        SET t_ftid = CONCAT(
            SUBSTRING_INDEX(t_raw, ':', 1),
            '-',
            SUBSTRING(t_raw, LOCATE(':', t_raw) + 1)
        )
        WHERE t_raw LIKE '%-D%' OR t_raw LIKE '%-E%' OR 
              t_raw LIKE '%-G%' OR t_raw LIKE '%-M%' OR 
              t_raw LIKE '%-U%'
    )";

    if (mysql_query(conn, query_t_DEGMU.c_str())) {
        std::cerr << "更新 t_ftid (-DEGMU) 失败: " << mysql_error(conn) << std::endl;
        mysql_query(conn, "ROLLBACK");
        return false;
    }

    // --- 5. 处理 ":-" 的情况 ---
    std::string query_s_colon_dash = R"(
        UPDATE v_csv_raw
        SET s_ftid = REPLACE(s_raw, ':-', '-')
        WHERE s_raw LIKE '%:-%:%'
    )";

    if (mysql_query(conn, query_s_colon_dash.c_str())) {
        std::cerr << "更新 s_ftid (:-) 失败: " << mysql_error(conn) << std::endl;
        mysql_query(conn, "ROLLBACK");
        return false;
    }

    std::string query_t_colon_dash = R"(
        UPDATE v_csv_raw
        SET t_ftid = REPLACE(t_raw, ':-', '-')
        WHERE t_raw LIKE '%:-%:%'
    )";

    if (mysql_query(conn, query_t_colon_dash.c_str())) {
        std::cerr << "更新 t_ftid (:-) 失败: " << mysql_error(conn) << std::endl;
        mysql_query(conn, "ROLLBACK");
        return false;
    }




// 提交事务之前插入第六步：
// --- 6. 新增逻辑（例如提取设备和终端字段）---
std::string query_s_device = R"(
    UPDATE v_csv_raw
    SET s_device = SUBSTRING(
        s_ftid,
        LOCATE('-', s_ftid) + 1,
        LOCATE(':', s_ftid, LOCATE('-', s_ftid)) - LOCATE('-', s_ftid) - 1
    )
    WHERE s_ftid LIKE '%-%:%'
)";
if (mysql_query(conn, query_s_device.c_str())) {
    std::cerr << "更新失败: " << mysql_error(conn) << std::endl;
    mysql_query(conn, "ROLLBACK");
    return false;
}

// 提交事务
if (mysql_query(conn, "COMMIT")) {
    std::cerr << "提交事务失败: " << mysql_error(conn) << std::endl;
    return false;
}

    // --- 处理目标设备和终端 ---
    std::string query_t_device = R"(
        UPDATE v_csv_raw
        SET t_device = SUBSTRING(
            t_ftid,
            LOCATE('-', t_ftid) + 1,
            LOCATE(':', t_ftid, LOCATE('-', t_ftid)) - LOCATE('-', t_ftid) - 1
        )
        WHERE t_ftid LIKE '%-%:%'
    )";
    if (mysql_query(conn, query_t_device.c_str())) {
        std::cerr << "更新 t_device 失败: " << mysql_error(conn) << std::endl;
        mysql_query(conn, "ROLLBACK");
        return false;
    }

    std::string query_t_terminal = R"(
        UPDATE v_csv_raw
        SET t_terminal = SUBSTRING(t_ftid, LOCATE(':', t_ftid) + 1)
        WHERE t_ftid LIKE '%:%'
    )";
    if (mysql_query(conn, query_t_terminal.c_str())) {
        std::cerr << "更新 t_terminal 失败: " << mysql_error(conn) << std::endl;
        mysql_query(conn, "ROLLBACK");
        return false;
    }




    // 提交事务
    if (mysql_query(conn, "COMMIT")) {
        std::cerr << "提交事务失败: " << mysql_error(conn) << std::endl;
        return false;
    }

    std::cout << "数据格式化完成" << std::endl;
    return true;










}


private:
    // 批量插入数据
    bool batchInsertRows(const std::vector<CSVRow>& rows) {
        std::cout << "开始批量插入数据..." << std::endl;
        
        if (mysql_query(conn, "START TRANSACTION")) {
            std::cerr << "开始事务失败: " << mysql_error(conn) << std::endl;
            return false;
        }

        bool success = true;
        int insertedCount = 0;
        for (const auto& row : rows) {
            if (!row.s_raw.empty() && !row.t_raw.empty()) {
                std::string query = "INSERT INTO " + tableName + 
                    " (cnumber, s_raw, s_ftid, s_function, s_location, s_device, s_terminal, "
                    "  t_raw, t_ftid, t_function, t_location, t_device, t_terminal) VALUES ("
                    "'" + escapeString(row.cnumber) + "', "
                    "'" + escapeString(row.s_raw) + "', "
                    "'" + escapeString(row.s_ftid) + "', "
                    "'" + escapeString(row.s_function) + "', "
                    "'" + escapeString(row.s_location) + "', "
                    "'" + escapeString(row.s_device) + "', "
                    "'" + escapeString(row.s_terminal) + "', "
                    "'" + escapeString(row.t_raw) + "', "
                    "'" + escapeString(row.t_ftid) + "', "
                    "'" + escapeString(row.t_function) + "', "
                    "'" + escapeString(row.t_location) + "', "
                    "'" + escapeString(row.t_device) + "', "
                    "'" + escapeString(row.t_terminal) + "')";

                if (mysql_query(conn, query.c_str()) != 0) {
                    std::cerr << "插入失败: " << mysql_error(conn) << std::endl;
                    success = false;
                    break;
                }
                insertedCount++;
                if (insertedCount % 100 == 0) {
                    std::cout << "已插入 " << insertedCount << " 条记录..." << std::endl;
                }
            }
        }

        if (success) {
            if (mysql_query(conn, "COMMIT")) {
                std::cerr << "提交事务失败: " << mysql_error(conn) << std::endl;
                return false;
            }
            std::cout << "成功插入 " << insertedCount << " 条记录" << std::endl;
            return true;
        } else {
            std::cout << "导入失败，正在回滚..." << std::endl;
            if (mysql_query(conn, "ROLLBACK")) {
                std::cerr << "回滚事务失败: " << mysql_error(conn) << std::endl;
            }
            return false;
        }
    }
};

int main() {
    SetConsoleOutputCP(CP_UTF8);
    std::cout << "程序开始运行..." << std::endl;
    
    try {
        std::cout << "加载数据库配置..." << std::endl;
        auto dbConfig = DbConfig::loadFromJson("config.json");

        std::cout << "创建 CSVImporter 实例..." << std::endl;
        CSVImporter importer("v_csv_raw", dbConfig);

        std::cout << "请选择要导入的CSV文件..." << std::endl;
        if (!importer.selectCSVFile()) {
            std::cout << "文件选择失败，程序退出" << std::endl;
            return 1;
        }
        
        std::cout << "开始导入数据..." << std::endl;
        if (importer.importFromCSV()) {
            std::cout << "数据导入成功" << std::endl;
       
       
       
       
            if (!importer.formatData()) {
                std::cerr << "数据格式化失败" << std::endl;
                return 1;
            }
       
       
        } else {
            std::cout << "数据导入失败" << std::endl;
            return 1;
        }



    } catch (const std::exception& e) {
        std::cerr << "错误: " << e.what() << std::endl;
        return 1;
    }

    std::cout << "程序正常结束" << std::endl;
    return 0;
}