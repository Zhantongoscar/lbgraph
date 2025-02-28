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
    string line;
    int line_count = 0;
    int records_read = 0;

    // 跳过 BOM Report 行和 BOM Usage Attributes 行
    getline(file, line);
    getline(file, line);
    
    // 读取字段标题行
    getline(file, line);
    
    // 开始读取数据行
    while (getline(file, line)) {  // 移除 MAX_RECORDS 限制
        vector<string> fields;
        string current_field;
        bool in_quoted_field = false;
        
        // 手动解析CSV，正确处理引号
        for (size_t i = 0; i < line.length(); i++) {
            char c = line[i];
            if (c == '"') {
                if (in_quoted_field && i + 1 < line.length() && line[i + 1] == '"') {
                    current_field += '"';
                    i++;
                } else {
                    in_quoted_field = !in_quoted_field;
                }
            } else if (c == ',' && !in_quoted_field) {
                fields.push_back(parseCSVField(current_field));
                current_field.clear();
            } else {
                current_field += c;
            }
        }
        fields.push_back(parseCSVField(current_field));

        // 确保有足够的字段
        if (fields.size() >= 40) {  // 按实际CSV文件的字段数调整
            DeviceInfo device;
            int field_index = 0;
            device.level = fields[field_index++];
            device.number = fields[field_index++];
            device.type = fields[field_index++];
            device.assembly_mode = fields[field_index++];
            field_index = 8; // Skip to name field
            device.name = fields[field_index++];
            field_index = 17; // Skip to operating element
            device.operating_element = fields[field_index++];
            device.bom_class = fields[field_index++];
            field_index = 23; // Skip to Chinese name
            device.name_zh_chs = fields[field_index++];
            field_index = 34; // Skip to comparable
            device.comparable = fields[field_index++];
            device.configuration_type = fields[field_index++];
            device.default_unit = fields[field_index++];
            device.reuse_not_allowed = fields[field_index++];
            device.old_part_number = fields[field_index++];
            device.machine_type = fields[field_index++];
            
            // 只添加非空记录
            if (!device.level.empty() && device.level != "Level") {
                data.push_back(device);
                records_read++;
                cout << "已读取第 " << records_read << " 条记录, Level值: " << device.level 
                     << ", Number: " << device.number << endl;
            }
        }
    }

    cout << "共读取 " << data.size() << " 行数据" << endl;
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

    // 创建表 leybold_device_lib - 添加id列
    string create_table_query = "CREATE TABLE leybold_device_lib ("
        "id INT PRIMARY KEY AUTO_INCREMENT, "  // 添加自增ID列
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
