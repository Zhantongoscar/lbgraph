#include <iostream>
#include "include/nlohmann/json.hpp"

int main() {
    std::cout << "Testing compilation..." << std::endl;
    nlohmann::json j = {{"test", "value"}};
    std::cout << j.dump(4) << std::endl;
    return 0;
}