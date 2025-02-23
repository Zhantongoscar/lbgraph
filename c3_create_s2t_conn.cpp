#include <Windows.h>
#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>
#include <map>
#include <set>
#include <algorithm>
#include <cstdlib>
#include "include/nlohmann/json.hpp"

using json = nlohmann::json;

// Device vertex structure
struct DeviceVertex {
    std::string id;
    std::string name;
    std::string function;
    std::string location;
    std::string device;
    std::string terminal;
    std::string type;  // panel, PLC, or field
};

// Wire properties structure
struct WireProperties {
    std::string wire_number;
    std::string cable_type;
    std::string color;
    std::string length;
    std::string bundle;
    std::string remark;
};

class Neo4jConnector {
private:
    std::string neo4jUri;
    std::string auth;  // Basic auth header value
    std::string csvPath;
    std::string projectNumber;

    // Base64编码
    static std::string base64_encode(const std::vector<unsigned char>& buf) {
        static const char base64_chars[] =
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

        std::string ret;
        int i = 0;
        int j = 0;
        unsigned char char_array_3[3];
        unsigned char char_array_4[4];

        for (unsigned char c : buf) {
            char_array_3[i++] = c;
            if (i == 3) {
                char_array_4[0] = (char_array_3[0] & 0xfc) >> 2;
                char_array_4[1] = ((char_array_3[0] & 0x03) << 4) + ((char_array_3[1] & 0xf0) >> 4);
                char_array_4[2] = ((char_array_3[1] & 0x0f) << 2) + ((char_array_3[2] & 0xc0) >> 6);
                char_array_4[3] = char_array_3[2] & 0x3f;

                for (i = 0; i < 4; i++)
                    ret += base64_chars[char_array_4[i]];
                i = 0;
            }
        }

        if (i) {
            for (j = i; j < 3; j++)
                char_array_3[j] = '\0';

            char_array_4[0] = (char_array_3[0] & 0xfc) >> 2;
            char_array_4[1] = ((char_array_3[0] & 0x03) << 4) + ((char_array_3[1] & 0xf0) >> 4);
            char_array_4[2] = ((char_array_3[1] & 0x0f) << 2) + ((char_array_3[2] & 0xc0) >> 6);

            for (j = 0; j < i + 1; j++)
                ret += base64_chars[char_array_4[j]];

            while (i++ < 3)
                ret += '=';
        }

        return ret;
    }

    // 从config.json读取配置
    bool loadConfig() {
        try {
            std::cout << "尝试打开config.json..." << std::endl;
            std::ifstream configFile("config.json");
            if (!configFile.is_open()) {
                std::cerr << "无法打开config.json文件" << std::endl;
                return false;
            }
            std::cout << "成功打开config.json" << std::endl;

            std::string jsonStr;
            std::string line;
            while (std::getline(configFile, line)) {
                jsonStr += line;
            }

            // 从json字符串解析配置
            json config = json::parse(jsonStr);

            // 获取Neo4j配置
            neo4jUri = config["neo4j"]["uri"];
            std::string username = config["neo4j"]["username"];
            std::string password = config["neo4j"]["password"];

            // 构建Basic Auth字符串
            std::string auth_str = username + ":" + password;
            std::vector<unsigned char> auth_vec(auth_str.begin(), auth_str.end());
            auth = base64_encode(auth_vec);

            // 获取文件配置
            csvPath = config["files"]["csv_path"];
            projectNumber = config["files"]["project_number"];

            return true;
        }
        catch (const std::exception& e) {
            std::cerr << "读取配置文件错误: " << e.what() << std::endl;
            return false;
        }
    }

    // 执行Cypher查询
    bool executeCypher(const std::string& query, const json& params) {
        json requestBody = {
            {"statements", {
                {
                    {"statement", query},
                    {"parameters", params}
                }
            }}
        };

        std::string requestBodyStr = requestBody.dump();
        
        // Save request body to temporary file
        std::string tempFile = "temp_request.json";
        {
            std::ofstream outFile(tempFile);
            outFile << requestBodyStr;
        }

        // Create PowerShell command
        std::ostringstream cmdStream;
        cmdStream << "powershell -Command \"";
        cmdStream << "$headers = @{";
        cmdStream << "'Content-Type'='application/json';";
        cmdStream << "'Authorization'='Basic " << auth << "'";
        cmdStream << "}; ";
        cmdStream << "$body = Get-Content -Raw -Path '" << tempFile << "'; ";
        cmdStream << "Invoke-WebRequest -Uri '" << neo4jUri << "/db/data/cypher' ";
        cmdStream << "-Method Post -Headers $headers -Body $body -UseBasicParsing";
        cmdStream << "\"";

        // Execute command
        int result = system(cmdStream.str().c_str());

        // Clean up temp file
        std::remove(tempFile.c_str());

        return result == 0;
    }

    // 检查端子是否为PE或N
    bool isPeOrNTerminal(const std::string& terminal) {
        std::string upperTerm = terminal;
        std::transform(upperTerm.begin(), upperTerm.end(), upperTerm.begin(), ::toupper);
        return (upperTerm.find("PE") != std::string::npos) || (upperTerm == "N");
    }

    // 获取顶点ID
    std::string getVertexId(const std::string& nodeStr) {
        std::string trimmed = nodeStr;
        // 移除前后空格
        while (!trimmed.empty() && isspace(trimmed.front())) trimmed.erase(0, 1);
        while (!trimmed.empty() && isspace(trimmed.back())) trimmed.pop_back();
        
        size_t plusPos = trimmed.find('+');
        if (plusPos != std::string::npos) {
            return trimmed.substr(plusPos + 1);
        }
        return trimmed;
    }

    // 解析节点属性
    DeviceVertex parseNodeProperties(const std::string& nodeStr) {
        DeviceVertex vertex;
        vertex.name = nodeStr;

        // 检查并添加默认标记
        std::string processedStr = nodeStr;
        if (nodeStr.find('=') == std::string::npos && 
            nodeStr.find('+') == std::string::npos && 
            nodeStr.find('-') == std::string::npos && 
            nodeStr.find(':') == std::string::npos) {
            processedStr = "=+" + nodeStr;
        }

        // 确保有冒号分隔符
        if (processedStr.find(':') == std::string::npos) {
            size_t lastDash = processedStr.rfind('-');
            if (lastDash != std::string::npos) {
                processedStr.insert(lastDash + 1, ":");
            } else {
                processedStr += ":";
            }
        }

        // 解析各个部分
        size_t equalPos = processedStr.find('=');
        size_t plusPos = processedStr.find('+');
        size_t dashPos = processedStr.find('-');
        size_t colonPos = processedStr.find(':');

        if (equalPos == std::string::npos) equalPos = 0;

        if (plusPos != std::string::npos) {
            // 提取function
            vertex.function = processedStr.substr(equalPos + 1, plusPos - (equalPos + 1));
            
            if (dashPos != std::string::npos) {
                // 提取location
                vertex.location = processedStr.substr(plusPos + 1, dashPos - (plusPos + 1));
                
                if (colonPos != std::string::npos) {
                    // 提取device
                    vertex.device = processedStr.substr(dashPos + 1, colonPos - (dashPos + 1));
                    
                    // 设置type
                    if (!vertex.device.empty()) {
                        if (vertex.device[0] == 'A') {
                            vertex.type = "PLC";
                        } else if (vertex.location.substr(0, 3) != "K1.") {
                            vertex.type = "field";
                        } else {
                            vertex.type = "panel";
                        }
                    }

                    // 提取terminal
                    vertex.terminal = processedStr.substr(colonPos + 1);
                }
            }
        }

        // 移除各字段前后空格
        auto trim = [](std::string& s) {
            while (!s.empty() && isspace(s.front())) s.erase(0, 1);
            while (!s.empty() && isspace(s.back())) s.pop_back();
        };

        trim(vertex.function);
        trim(vertex.location);
        trim(vertex.device);
        trim(vertex.terminal);

        return vertex;
    }

public:
    Neo4jConnector() {
        // 设置字符编码
        SetConsoleOutputCP(CP_UTF8);
        
        // 加载配置
        if (!loadConfig()) {
            throw std::runtime_error("加载配置失败");
        }
    }

    // 获取CSV路径
    std::string getCsvPath() const {
        return csvPath;
    }

    // 获取项目编号
    std::string getProjectNumber() const {
        return projectNumber;
    }

    // Parse CSV line into fields
    std::vector<std::string> parseCSVLine(const std::string& line) {
        std::vector<std::string> fields;
        std::string field;
        bool inQuotes = false;
        std::ostringstream currentField;

        for (char c : line) {
            if (c == '"') {
                inQuotes = !inQuotes;
            } else if (c == ',' && !inQuotes) {
                fields.push_back(currentField.str());
                currentField.str("");
                currentField.clear();
            } else {
                currentField << c;
            }
        }
        fields.push_back(currentField.str());
        return fields;
    }

    // 导入数据
    bool importData() {
        std::cout << "开始导入数据..." << std::endl;
        std::ifstream file(csvPath);
        if (!file.is_open()) {
            std::cerr << "无法打开CSV文件: " << csvPath << std::endl;
            return false;
        }

        // 跳过前两行
        std::string line;
        std::getline(file, line);
        std::getline(file, line);

        int count = 0;
        int lineNum = 0;

        while (std::getline(file, line)) {
            lineNum++;
            std::cout << "\n处理第 " << lineNum << " 行" << std::endl;

            std::vector<std::string> fields = parseCSVLine(line);

            if (fields.size() < 9) {  // 确保至少有source和target字段
                continue;
            }

            // 解析source和target
            std::string sourceStr = fields[7];
            std::string targetStr = fields[8];

            // 获取vertex IDs和属性
            DeviceVertex sourceVertex = parseNodeProperties(sourceStr);
            sourceVertex.id = getVertexId(sourceStr);

            DeviceVertex targetVertex = parseNodeProperties(targetStr);
            targetVertex.id = getVertexId(targetStr);

            // 检查是否跳过PE/N连接
            if (isPeOrNTerminal(sourceVertex.terminal) || isPeOrNTerminal(targetVertex.terminal)) {
                std::cout << "跳过PE/N连接" << std::endl;
                continue;
            }

            // 创建连接属性
            WireProperties wire;
            wire.wire_number = fields[0];
            wire.cable_type = fields[2];
            wire.color = fields[4];
            wire.length = fields[6];
            wire.bundle = fields[13];
            wire.remark = fields[16];

            // 只处理panel和PLC之间的连接
            if ((sourceVertex.type == "panel" || sourceVertex.type == "PLC") &&
                (targetVertex.type == "panel" || targetVertex.type == "PLC")) {
                
                // 准备Cypher查询参数
                json params = {
                    {"source_props", {
                        {"id", sourceVertex.id},
                        {"name", sourceVertex.name},
                        {"function", sourceVertex.function},
                        {"location", sourceVertex.location},
                        {"device", sourceVertex.device},
                        {"terminal", sourceVertex.terminal},
                        {"type", sourceVertex.type}
                    }},
                    {"target_props", {
                        {"id", targetVertex.id},
                        {"name", targetVertex.name},
                        {"function", targetVertex.function},
                        {"location", targetVertex.location},
                        {"device", targetVertex.device},
                        {"terminal", targetVertex.terminal},
                        {"type", targetVertex.type}
                    }},
                    {"wire_props", {
                        {"wire_number", wire.wire_number},
                        {"cable_type", wire.cable_type},
                        {"color", wire.color},
                        {"length", wire.length},
                        {"bundle", wire.bundle},
                        {"remark", wire.remark}
                    }}
                };

                // Cypher查询
                std::string query = 
                    "MERGE (source:Vertex {id: $source_props.id}) "
                    "SET source += $source_props "
                    "MERGE (target:Vertex {id: $target_props.id}) "
                    "SET target += $target_props "
                    "MERGE (source)-[c:conn]->(target) "
                    "SET c = $wire_props "
                    "MERGE (target)-[c2:conn]->(source) "
                    "SET c2 = $wire_props";

                count++;

                if (count % 100 == 0) {
                    std::cout << "已处理 " << count << " 条连接" << std::endl;
                }
            }

            // Test mode: only process first 2000 lines
            if (lineNum >= 5) {
                std::cout << "已处理2000行数据，停止测试" << std::endl;
                break;
            }
        }

        std::cout << "数据导入完成，共处理 " << count << " 条连接" << std::endl;
        return true;
    }
};

// int main() {
//     std::cout << "程序开始执行..." << std::endl; // Add this line
//     try {
//         Neo4jConnector connector;
//         connector.importData();
//     }
//     catch (const std::exception& e) {
//         std::cerr << "错误: " << e.what() << std::endl;
//         return 1;
//     }
//     std::cout << "程序执行完成..." << std::endl; // Add this line
//     return 0;
// }



int main() {
    // 设置控制台编码为 UTF-8
    SetConsoleOutputCP(CP_UTF8);
    SetConsoleCP(CP_UTF8);

    std::cout << "程序开始执行..." << std::endl;
    try {
        Neo4jConnector connector;
        connector.importData();
    }
    catch (const std::exception& e) {
        std::cerr << "错误: " << e.what() << std::endl;
        return 1;
    }
    std::cout << "程序执行完成..." << std::endl;
    return 0;
}