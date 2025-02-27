#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <filesystem>
#include <nlohmann/json.hpp>
// 请确保将 C:\clib\mysql\include 添加到编译器的 includePath 中
#include "mysql.h"

namespace fs = std::filesystem;
using json = nlohmann::json;

int main(){
    // 扫描 data 目录下所有的 Excel 文件
    std::string data_path = "data";
    std::vector<fs::directory_entry> excel_files;
    for(auto &entry : fs::directory_iterator(data_path)){
        if(entry.is_regular_file()){
            std::string ext = entry.path().extension().string();
            if(ext == ".xls" || ext == ".xlsx" || ext == ".xlsm"){
                excel_files.push_back(entry);
            }
        }
    }
    if(excel_files.empty()){
        std::cerr << "没有找到Excel文件" << std::endl;
        return 1;
    }
    std::cout << "请选择要打开的Excel文件：" << std::endl;
    for(size_t i = 0; i < excel_files.size(); ++i){
        std::cout << (i + 1) << ": " << excel_files[i].path().string() << std::endl;
    }
    std::cout << "请输入选择的序号: ";
    int choice = 0;
    std::cin >> choice;
    if(choice < 1 || choice > static_cast<int>(excel_files.size())){
        std::cerr << "选择无效" << std::endl;
        return 1;
    }
    std::string filename = excel_files[choice - 1].path().string();
    std::ifstream file(filename, std::ios::binary);
    if(!file){
        std::cerr << "无法打开文件: " << filename << std::endl;
        return 1;
    }
    std::cout << "文件已成功打开: " << filename << std::endl;
    file.close();

    // 模拟读取 Excel 数据，假设 Excel 中有两列数据：device_id 和 device_name
    std::vector<std::pair<int, std::string>> excel_data;
    excel_data.push_back({1, "DeviceA"});
    excel_data.push_back({2, "DeviceB"});

    // 读取 config.json 中的数据库连接信息
    std::ifstream config_file("config.json");
    if(!config_file){
        std::cerr << "无法打开 config.json" << std::endl;
        return 1;
    }
    json config;
    try {
        config_file >> config;
    } catch(const std::exception &e){
        std::cerr << "解析 config.json 失败: " << e.what() << std::endl;
        return 1;
    }
    config_file.close();

    std::string host = config["mysql"]["host"];
    std::string user = config["mysql"]["user"];
    std::string password = config["mysql"]["password"];
    std::string dbname = config["mysql"]["database"];

    // 使用 MySQL C API 连接数据库
    MYSQL *conn = mysql_init(nullptr);
    if(!conn){
        std::cerr << "mysql_init 失败" << std::endl;
        return 1;
    }
    if(!mysql_real_connect(conn, host.c_str(), user.c_str(), password.c_str(), dbname.c_str(), 3306, nullptr, 0)){
        std::cerr << "连接数据库失败: " << mysql_error(conn) << std::endl;
        mysql_close(conn);
        return 1;
    }
    std::cout << "成功连接到数据库" << std::endl;

    // 创建表 leybold_device_lib（如果不存在）
    std::string create_table_query = "CREATE TABLE IF NOT EXISTS leybold_device_lib ("
                                     "device_id INT PRIMARY KEY, "
                                     "device_name VARCHAR(100)"
                                     ");";
    if(mysql_query(conn, create_table_query.c_str())){
        std::cerr << "创建表失败: " << mysql_error(conn) << std::endl;
        mysql_close(conn);
        return 1;
    }

    // 插入数据到 leybold_device_lib 表中
    for(const auto &row : excel_data){
        std::string insert_query = "REPLACE INTO leybold_device_lib (device_id, device_name) VALUES ("
                                   + std::to_string(row.first) + ", '"
                                   + row.second + "');";
        if(mysql_query(conn, insert_query.c_str())){
            std::cerr << "插入数据失败: " << mysql_error(conn) << std::endl;
            mysql_close(conn);
            return 1;
        }
    }
    std::cout << "Excel数据已成功保存到数据库表 leybold_device_lib" << std::endl;
    mysql_close(conn);
    return 0;
}
