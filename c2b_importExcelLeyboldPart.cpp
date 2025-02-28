#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <filesystem>
#include <sstream>
#include "include/nlohmann/json.hpp"
#include "C:/clib/mysql/include/mysql.h"

namespace fs = std::filesystem;
using json = nlohmann::json;
using namespace std;

struct DeviceInfo {
    string level;             // Level
    string number;           // Number
    string type;             // Type
    string assembly_mode;    // Assembly Mode
    string name;             // Name
    string operating_element; // Operating Element
    string bom_class;        // BOM Class
    string name_zh_chs;      // Chinese Name
    string comparable;       // Comparable
    string configuration_type; // Configuration Type
    string default_unit;     // Default Unit
    string reuse_not_allowed; // Reuse Not Allowed
    string old_part_number;  // Old Part Number
    string machine_type;     // Machine Type
    string basic_material;
    string basic_material_desc;
    string supersede;
    string superseded_by;
    string material_group;
    string no_logistic_relevance;
    string dangerous_good_indic;
    string class_node;
    string legacy_id;
    string electrical_relevant;
    string doc_classification;
    string stackability;
    string delta_x;
    string delta_y;
    string delta_z;
    string mass;
    string length;
    string width;
    string height;
    string netto_weight;
    string weight_unit;
    string weight_code;
    string service_life;
    string spc_termination;
    string design_office;
    string division;
    string modified_by;
    string last_modified;
};

// Helper function to properly handle quoted CSV fields
string parseCSVField(string &field) {
    // Remove whitespace
    field.erase(0, field.find_first_not_of(" \t\r\n"));
    field.erase(field.find_last_not_of(" \t\r\n") + 1);
    
    // Remove quotes if present
    if (field.size() >= 2 && field.front() == '"' && field.back() == '"') {
        field = field.substr(1, field.length() - 2);
        
        // Handle escaped quotes
        size_t pos = 0;
        while ((pos = field.find("\"\"", pos)) != string::npos) {
            field.replace(pos, 2, "\"");
            pos += 1;
        }
    }
    return field;
}

// Helper function to join strings with a delimiter
string join(const vector<string>& elements, const string& delimiter) {
    string result;
    for (size_t i = 0; i < elements.size(); ++i) {
        result += elements[i];
        if (i < elements.size() - 1) {
            result += delimiter;
        }
    }
    return result;
}

// 读取csv文件
vector<DeviceInfo> readExcelData(const string &filename) {
    vector<DeviceInfo> data;
    ifstream file(filename);
    if (!file.is_open()) {
        cerr << "无法打开文件: " << filename << endl;
        return data;
    }

    cout << "已读取文件: " << filename << endl;
    string content;
    string line;
    int line_num = 0;
    int records_read = 0;
    int skipped_lines = 0;

    // 先读取整个文件内容
    string full_content;
    while (getline(file, line)) {
        full_content += line + "\n";
    }
    
    // 手动解析整个内容
    vector<string> rows;
    string current_row;
    bool in_quotes = false;
    
    for (size_t i = 0; i < full_content.length(); i++) {
        char c = full_content[i];
        
        // 处理引号
        if (c == '"') {
            if (in_quotes && i + 1 < full_content.length() && full_content[i + 1] == '"') {
                current_row += '"';
                i++;
            } else {
                in_quotes = !in_quotes;
                current_row += c;
            }
        }
        // 如果在引号外遇到换行符,说明是真正的行结束
        else if (c == '\n' && !in_quotes) {
            rows.push_back(current_row);
            current_row.clear();
        }
        // 其他情况直接添加字符
        else {
            current_row += c;
        }
    }
    if (!current_row.empty()) {
        rows.push_back(current_row);
    }

    // 处理每一行
    for (size_t row_num = 0; row_num < rows.size(); row_num++) {
        line_num++;
        string &row = rows[row_num];
        
        if(row.empty()) {
            skipped_lines++;
            continue;
        }
        
        // 跳过前两行和标题行
        if (line_num <= 3) {
            skipped_lines++;
            continue;
        }

        // 详细输出140-150行的信息
        if(line_num >= 140 && line_num <= 150) {
            cout << "\n===============================";
            cout << "\n处理第 " << line_num << " 行:";
            cout << "\n原始行内容:" << endl;
            cout << row << endl;
            
            cout << "\nASCII码表示:" << endl;
            for(char c : row) {
                cout << (int)c << "(" << c << ") ";
            }
            cout << endl;
        }
        
        vector<string> fields;
        string current_field;
        bool in_quoted_field = false;
        
        // 手动解析CSV，正确处理引号
        if(line_num >= 140 && line_num <= 150) {
            cout << "\n字段解析过程:" << endl;
        }

        for (size_t i = 0; i < row.length(); i++) {
            char c = row[i];
            if (c == '"') {
                if (in_quoted_field && i + 1 < row.length() && row[i + 1] == '"') {
                    if(line_num >= 140 && line_num <= 150) {
                        cout << "发现连续引号(\"\"), 转义为单引号" << endl;
                    }
                    current_field += '"';
                    i++;
                } else {
                    if(line_num >= 140 && line_num <= 150) {
                        cout << "切换引号状态: " << (in_quoted_field ? "退出" : "进入") << "引号区域" << endl;
                    }
                    in_quoted_field = !in_quoted_field;
                }
            } else if (c == ',' && !in_quoted_field) {
                if(line_num >= 140 && line_num <= 150) {
                    cout << "发现字段分隔符, 当前字段内容: [" << current_field << "]" << endl;
                }
                fields.push_back(parseCSVField(current_field));
                current_field.clear();
            } else {
                current_field += c;
            }
        }
        fields.push_back(parseCSVField(current_field));

        if(line_num >= 140 && line_num <= 150) {
            cout << "\n最终解析结果:" << endl;
            cout << "解析出的字段数量: " << fields.size() << endl;
            for(size_t i = 0; i < fields.size(); i++) {
                cout << "字段[" << i << "]: [" << fields[i] << "]" << endl;
            }
            cout << "===============================\n" << endl;
        }

        // 减少字段数量要求到实际需要的数量
        if (fields.size() >= 24) {  
            DeviceInfo device;
            try {
                device.level = fields[0];
                device.number = fields[1];
                device.type = fields[2];
                device.assembly_mode = fields[3];
                device.name = fields[8];
                device.operating_element = fields[17];
                device.bom_class = fields[18];
                device.name_zh_chs = fields[23];
                
                // 修改判断逻辑：只要任一关键字段不为空就保存
                if (!device.number.empty() || !device.name.empty()) {
                    // 替换字段中的换行符为空格
                    auto replaceNewlines = [](string& str) {
                        size_t pos;
                        while ((pos = str.find("\n")) != string::npos) {
                            str.replace(pos, 1, " ");
                        }
                        while ((pos = str.find("\r")) != string::npos) {
                            str.replace(pos, 1, " ");
                        }
                    };
                    
                    replaceNewlines(device.level);
                    replaceNewlines(device.number);
                    replaceNewlines(device.type);
                    replaceNewlines(device.assembly_mode);
                    replaceNewlines(device.name);
                    replaceNewlines(device.operating_element);
                    replaceNewlines(device.bom_class);
                    replaceNewlines(device.name_zh_chs);
                    
                    data.push_back(device);
                    records_read++;
                    if (records_read % 100 == 0) {
                        cout << "已读取 " << records_read << " 条记录..." << endl;
                    }
                } else {
                    skipped_lines++;
                }
            } catch (const exception& e) {
                cerr << "处理第 " << line_num << " 行时出错: " << e.what() << endl;
                skipped_lines++;
                continue;
            }
        } else {
            if(line_num >= 140 && line_num <= 150) {
                cerr << "第 " << line_num << " 行字段数量不足: 期望24个字段，实际" << fields.size() << "个字段" << endl;
                cout << "行内容: " << row << endl;
            }
            skipped_lines++;
        }
    }

    cout << "\n处理完成统计:" << endl;
    cout << "总行数: " << line_num << endl;
    cout << "跳过行数: " << skipped_lines << endl;
    cout << "成功读取: " << data.size() << " 行数据" << endl;
    return data;
}

int main() {
    // 扫描 data 目录下所有的 Excel 文件
    string data_path = "data";
    vector<fs::directory_entry> excel_files;
    for (const auto &entry : fs::directory_iterator(data_path)) {
        if (entry.is_regular_file()) {
            string ext = entry.path().extension().string();
            if (ext == ".csv") {  // 修改为只读取CSV文件
                excel_files.push_back(entry);
            }
        }
    }

    if (excel_files.empty()) {
        cerr << "未找到Excel文件" << endl;
        return 1;
    }

    // 显示文件列表供用户选择
    cout << "请选择要打开的Excel文件：" << endl;
    for (size_t i = 0; i < excel_files.size(); i++) {
        cout << i + 1 << ": " << excel_files[i].path().string() << endl;
    }

    size_t choice;
    cout << "请输入选择的序号: ";
    cin >> choice;

    if (choice < 1 || choice > excel_files.size()) {
        cerr << "无效的选择" << endl;
        return 1;
    }

    string filename = excel_files[choice - 1].path().string();
    cout << "正在读取Excel文件，请稍候..." << endl;

    // 读取Excel数据
    vector<DeviceInfo> excel_data = readExcelData(filename);
    if(excel_data.empty()) {
        cerr << "无法读取Excel数据" << endl;
        return 1;
    }

    // 读取 config.json 中的数据库连接信息
    ifstream config_file("config.json");
    if (!config_file) {
        cerr << "无法打开 config.json" << endl;
        return 1;
    }
    json config;
    try {
        config_file >> config;
    } catch (const exception &e) {
        cerr << "解析 config.json 失败: " << e.what() << endl;
        return 1;
    }
    config_file.close();

    string host = config["mysql"]["host"];
    string user = config["mysql"]["user"];
    string password = config["mysql"]["password"];
    string dbname = config["mysql"]["database"];

    // 使用 MySQL C API 连接数据库
    MYSQL *conn = mysql_init(nullptr);
    if (!conn) {
        cerr << "mysql_init 失败" << endl;
        return 1;
    }
    
    // 设置字符编码
    mysql_options(conn, MYSQL_SET_CHARSET_NAME, "utf8mb4");
    mysql_options(conn, MYSQL_INIT_COMMAND, "SET NAMES utf8mb4");
    
    if (!mysql_real_connect(conn, host.c_str(), user.c_str(), password.c_str(), dbname.c_str(), 3306, nullptr, 0)) {
        cerr << "连接数据库失败: " << mysql_error(conn) << endl;
        mysql_close(conn);
        return 1;
    }
    cout << "成功连接到数据库" << endl;

    // 先删除表（如果存在）
    string drop_table_query = "DROP TABLE IF EXISTS leybold_device_lib;";
    if (mysql_query(conn, drop_table_query.c_str())) {
        cerr << "删除表失败: " << mysql_error(conn) << endl;
        mysql_close(conn);
        return 1;
    }

    // 创建表 leybold_device_lib - 调整列顺序
    string create_table_query = "CREATE TABLE leybold_device_lib ("
        "id INT PRIMARY KEY AUTO_INCREMENT, "  // id放在最前面
        "level TEXT, "
        "number TEXT, "
        "type TEXT, "
        "assembly_mode TEXT, "
        "name TEXT, "
        "operating_element TEXT, "
        "bom_class TEXT, "
        "name_zh_chs TEXT"
        ") CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;";
    if (mysql_query(conn, create_table_query.c_str())) {
        cerr << "创建表失败: " << mysql_error(conn) << endl;
        mysql_close(conn);
        return 1;
    }

    // 插入数据到 leybold_device_lib 表中
    for (const auto &device : excel_data) {
        vector<pair<string, string>> fields = {
            {"level", device.level},
            {"number", device.number}, 
            {"type", device.type},
            {"assembly_mode", device.assembly_mode},
            {"name", device.name},
            {"operating_element", device.operating_element},
            {"bom_class", device.bom_class},
            {"name_zh_chs", device.name_zh_chs}
        };

        vector<string> columns, values;
        for (const auto &field : fields) {
            if (!field.second.empty()) {
                columns.push_back(field.first);
                
                vector<char> escaped(field.second.length() * 2 + 1);
                mysql_real_escape_string(conn, escaped.data(), field.second.c_str(), field.second.length());
                values.push_back(string("'") + escaped.data() + "'");
            }
        }

        string insert_query = "INSERT INTO leybold_device_lib (" + 
            join(columns, ", ") + ") VALUES (" + join(values, ", ") + ")";

        if (mysql_query(conn, insert_query.c_str())) {
            cerr << "插入数据失败: " << mysql_error(conn) << endl;
            mysql_close(conn);
            return 1;
        }
    }
    cout << "已成功导入 " << excel_data.size() << " 条记录到数据库表 leybold_device_lib" << endl;
    mysql_close(conn);
    return 0;
}
