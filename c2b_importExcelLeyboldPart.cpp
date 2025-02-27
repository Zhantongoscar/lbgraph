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
    string comparable;
    string configuration_type;
    string default_unit;
    string reuse_not_allowed;
    string old_part_number;
    string machine_type;
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
    int records_read = 0;  // 添加记录计数器
    const int MAX_RECORDS = 10;  // 限制最大读取记录数

    while (getline(file, line) && records_read < MAX_RECORDS) {  // 添加记录数限制
        line_count++;
        if (line_count <= 2) {  // 跳过前两行
            continue;
        }

        DeviceInfo device;
        stringstream ss(line);
        string field;
        vector<string> fields;
        bool in_quoted_field = false;
        string current_field;
        
        // 手动解析CSV，正确处理引号
        for (size_t i = 0; i < line.length(); i++) {
            char c = line[i];
            if (c == '"') {
                if (in_quoted_field && i + 1 < line.length() && line[i + 1] == '"') {
                    // 处理转义的引号
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
        fields.push_back(parseCSVField(current_field)); // 添加最后一个字段

        // 确保字段数量正确
        while (fields.size() < 33) {  // 调整为实际字段数量
            fields.push_back("");
        }

        // 按新的字段顺序赋值
        device.comparable = fields[0];
        device.configuration_type = fields[1];
        device.default_unit = fields[2];
        device.reuse_not_allowed = fields[3];
        device.old_part_number = fields[4];
        device.machine_type = fields[5];
        device.basic_material = fields[6];
        device.basic_material_desc = fields[7];
        device.supersede = fields[8];
        device.superseded_by = fields[9];
        device.material_group = fields[10];
        device.no_logistic_relevance = fields[11];
        device.dangerous_good_indic = fields[12];
        device.class_node = fields[13];
        device.legacy_id = fields[14];
        device.electrical_relevant = fields[15];
        device.doc_classification = fields[16];
        device.stackability = fields[17];
        device.delta_x = fields[18];
        device.delta_y = fields[19];
        device.delta_z = fields[20];
        device.mass = fields[21];
        device.length = fields[22];
        device.width = fields[23];
        device.height = fields[24];
        device.netto_weight = fields[25];
        device.weight_unit = fields[26];
        device.weight_code = fields[27];
        device.service_life = fields[28];
        device.spc_termination = fields[29];
        device.design_office = fields[30];
        device.division = fields[31];
        device.modified_by = fields[32];
        device.last_modified = fields.size() > 33 ? fields[33] : "";

        // 只添加非空行
        if (!device.comparable.empty() || !device.configuration_type.empty()) {
            data.push_back(device);
            records_read++;  // 增加记录计数
            cout << "已读取第 " << records_read << " 条记录" << endl;  // 添加进度显示
        }
    }

    cout << "已读取 " << data.size() << " 行数据" << endl;
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

    // 创建表 leybold_device_lib - 使用新的字段结构
    string create_table_query = "CREATE TABLE leybold_device_lib ("
        "comparable TEXT, "
        "configuration_type TEXT, "
        "default_unit TEXT, "
        "reuse_not_allowed TEXT, "
        "old_part_number TEXT, "
        "machine_type TEXT, "
        "basic_material TEXT, "
        "basic_material_desc TEXT, "
        "supersede TEXT, "
        "superseded_by TEXT, "
        "material_group TEXT, "
        "no_logistic_relevance TEXT, "
        "dangerous_good_indic TEXT, "
        "class_node TEXT, "
        "legacy_id TEXT, "
        "electrical_relevant TEXT, "
        "doc_classification TEXT, "
        "stackability TEXT, "
        "delta_x TEXT, "
        "delta_y TEXT, "
        "delta_z TEXT, "
        "mass TEXT, "
        "length TEXT, "
        "width TEXT, "
        "height TEXT, "
        "netto_weight TEXT, "
        "weight_unit TEXT, "
        "weight_code TEXT, "
        "service_life TEXT, "
        "spc_termination TEXT, "
        "design_office TEXT, "
        "division TEXT, "
        "modified_by TEXT, "
        "last_modified TEXT"
        ") CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;";
    if (mysql_query(conn, create_table_query.c_str())) {
        cerr << "创建表失败: " << mysql_error(conn) << endl;
        mysql_close(conn);
        return 1;
    }

    // 插入数据到 leybold_device_lib 表中
    for (const auto &device : excel_data) {
        vector<pair<string, string>> fields = {
            {"comparable", device.comparable},
            {"configuration_type", device.configuration_type},
            {"default_unit", device.default_unit},
            {"reuse_not_allowed", device.reuse_not_allowed},
            {"old_part_number", device.old_part_number},
            {"machine_type", device.machine_type},
            {"basic_material", device.basic_material},
            {"basic_material_desc", device.basic_material_desc},
            {"supersede", device.supersede},
            {"superseded_by", device.superseded_by},
            {"material_group", device.material_group},
            {"no_logistic_relevance", device.no_logistic_relevance},
            {"dangerous_good_indic", device.dangerous_good_indic},
            {"class_node", device.class_node},
            {"legacy_id", device.legacy_id},
            {"electrical_relevant", device.electrical_relevant},
            {"doc_classification", device.doc_classification},
            {"stackability", device.stackability},
            {"delta_x", device.delta_x},
            {"delta_y", device.delta_y},
            {"delta_z", device.delta_z},
            {"mass", device.mass},
            {"length", device.length},
            {"width", device.width},
            {"height", device.height},
            {"netto_weight", device.netto_weight},
            {"weight_unit", device.weight_unit},
            {"weight_code", device.weight_code},
            {"service_life", device.service_life},
            {"spc_termination", device.spc_termination},
            {"design_office", device.design_office},
            {"division", device.division},
            {"modified_by", device.modified_by},
            {"last_modified", device.last_modified}
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
