#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <map>
#include <windows.h>

// 设备类型结构体
struct DeviceType {
    int id;
    std::string name;
    std::string description;
    std::string manufacturer;
    std::string model;
};

class DeviceTypeTable {
private:
    std::map<int, DeviceType> devices;
    int nextId;
    std::string filename;

public:
    DeviceTypeTable(const std::string& file) : nextId(1), filename(file) {
        loadFromFile();
    }

    // 添加新设备类型
    bool addDeviceType(const std::string& name, const std::string& description,
                      const std::string& manufacturer, const std::string& model) {
        DeviceType device;
        device.id = nextId++;
        device.name = name;
        device.description = description;
        device.manufacturer = manufacturer;
        device.model = model;

        devices[device.id] = device;
        return saveToFile();
    }

    // 根据ID获取设备类型
    DeviceType* getDeviceType(int id) {
        auto it = devices.find(id);
        if (it != devices.end()) {
            return &(it->second);
        }
        return nullptr;
    }

    // 更新设备类型
    bool updateDeviceType(int id, const std::string& name, const std::string& description,
                         const std::string& manufacturer, const std::string& model) {
        if (devices.find(id) == devices.end()) {
            return false;
        }

        devices[id].name = name;
        devices[id].description = description;
        devices[id].manufacturer = manufacturer;
        devices[id].model = model;

        return saveToFile();
    }

    // 删除设备类型
    bool deleteDeviceType(int id) {
        if (devices.find(id) == devices.end()) {
            return false;
        }

        devices.erase(id);
        return saveToFile();
    }

    // 显示所有设备类型
    void displayAll() {
        std::cout << "\n设备类型列表：" << std::endl;
        std::cout << "----------------------------------------" << std::endl;
        for (const auto& pair : devices) {
            const DeviceType& device = pair.second;
            std::cout << "ID: " << device.id << std::endl;
            std::cout << "名称: " << device.name << std::endl;
            std::cout << "描述: " << device.description << std::endl;
            std::cout << "制造商: " << device.manufacturer << std::endl;
            std::cout << "型号: " << device.model << std::endl;
            std::cout << "----------------------------------------" << std::endl;
        }
    }

private:
    // 从文件加载数据
    bool loadFromFile() {
        std::ifstream file(filename);
        if (!file.is_open()) {
            return false;
        }

        devices.clear();
        nextId = 1;

        DeviceType device;
        std::string line;
        
        while (std::getline(file, line)) {
            if (line.empty()) continue;
            
            size_t pos = 0;
            std::string token;
            std::vector<std::string> tokens;
            
            while ((pos = line.find("|")) != std::string::npos) {
                token = line.substr(0, pos);
                tokens.push_back(token);
                line.erase(0, pos + 1);
            }
            tokens.push_back(line);

            if (tokens.size() == 5) {
                device.id = std::stoi(tokens[0]);
                device.name = tokens[1];
                device.description = tokens[2];
                device.manufacturer = tokens[3];
                device.model = tokens[4];

                devices[device.id] = device;
                if (device.id >= nextId) {
                    nextId = device.id + 1;
                }
            }
        }

        file.close();
        return true;
    }

    // 保存数据到文件
    bool saveToFile() {
        std::ofstream file(filename);
        if (!file.is_open()) {
            return false;
        }

        for (const auto& pair : devices) {
            const DeviceType& device = pair.second;
            file << device.id << "|"
                 << device.name << "|"
                 << device.description << "|"
                 << device.manufacturer << "|"
                 << device.model << "\n";
        }

        file.close();
        return true;
    }
};

int main() {
    // 设置控制台输出为UTF-8
    SetConsoleOutputCP(CP_UTF8);

    DeviceTypeTable table("device_types.txt");

    // 测试添加设备类型
    table.addDeviceType("继电器", "控制用继电器", "莱宝", "LB-001");
    table.addDeviceType("传感器", "温度传感器", "莱宝", "LB-002");

    // 显示所有设备
    table.displayAll();

    // 测试更新设备类型
    table.updateDeviceType(1, "高压继电器", "高压控制继电器", "莱宝", "LB-001-HV");

    // 显示更新后的结果
    std::cout << "\n更新后的设备列表：" << std::endl;
    table.displayAll();

    return 0;
}