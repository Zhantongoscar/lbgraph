# 项目
## 文件说明

CSV数据导入功能已完善。现在项目有三个主要工具:

import_csv_data.py - CSV数据导入工具

从CSV文件导入初始图数据
支持数据清理和转换
使用方法: python import_csv_data.py --csv_path data/SmartWiringzta.csv
sync_simulation.py - 仿真数据同步工具

从MySQL同步仿真设备数据
创建仿真节点和虚拟层
使用方法: python sync_simulation.py
graph_analysis.py - 图数据分析工具

分析Neo4j中的数据状态
提供多种分析查询
使用方法: python graph_analysis.py
所有工具都使用config.py中的统一配置,支持通过命令行参数覆盖默认设置。每个工具都专注于自己的职责,可以独立运行

## 
### 读取文件位置
python import_csv_data.py --csv_path temp/SmartWiringzta.csv


## 仿真测试板及单元信息
### 
/*
 Navicat Premium Dump SQL

 Source Server         : 192.168.35.10
 Source Server Type    : MySQL
 Source Server Version : 50744 (5.7.44)
 Source Host           : 192.168.35.10:3306
 Source Schema         : lbfat

 Target Server Type    : MySQL
 Target Server Version : 50744 (5.7.44)
 File Encoding         : 65001

 Date: 03/02/2025 10:50:30
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for devices
-- ----------------------------
DROP TABLE IF EXISTS `devices`;
CREATE TABLE `devices`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `project_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '项目名称',
  `module_type` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '模块类型',
  `serial_number` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT '序列号',
  `type_id` int(11) NOT NULL COMMENT '设备类型ID',
  `status` enum('online','offline') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT 'offline' COMMENT '设备状态',
  `rssi` int(11) NULL DEFAULT 0 COMMENT '信号强度',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uk_device`(`project_name`, `module_type`, `serial_number`) USING BTREE,
  INDEX `idx_project_name`(`project_name`) USING BTREE,
  INDEX `idx_status`(`status`) USING BTREE,
  INDEX `idx_type_id`(`type_id`) USING BTREE,
  CONSTRAINT `fk_project_name` FOREIGN KEY (`project_name`) REFERENCES `project_subscriptions` (`project_name`) ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT `fk_type_id` FOREIGN KEY (`type_id`) REFERENCES `device_types` (`id`) ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE = InnoDB AUTO_INCREMENT = 4 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '设备管理表' ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;

/*
 Navicat Premium Dump SQL

 Source Server         : 192.168.35.10
 Source Server Type    : MySQL
 Source Server Version : 50744 (5.7.44)
 Source Host           : 192.168.35.10:3306
 Source Schema         : lbfat

 Target Server Type    : MySQL
 Target Server Version : 50744 (5.7.44)
 File Encoding         : 65001

 Date: 03/02/2025 10:50:52
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for device_types
-- ----------------------------
DROP TABLE IF EXISTS `device_types`;
CREATE TABLE `device_types`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `type_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `point_count` int(11) NOT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `type_name`(`type_name`) USING BTREE
) ENGINE = InnoDB AUTO_INCREMENT = 19 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '设备类型定义表' ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;

###
/*
 Navicat Premium Dump SQL

 Source Server         : 192.168.35.10
 Source Server Type    : MySQL
 Source Server Version : 50744 (5.7.44)
 Source Host           : 192.168.35.10:3306
 Source Schema         : lbfat

 Target Server Type    : MySQL
 Target Server Version : 50744 (5.7.44)
 File Encoding         : 65001

 Date: 03/02/2025 23:34:23
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for device_type_points
-- ----------------------------
DROP TABLE IF EXISTS `device_type_points`;
CREATE TABLE `device_type_points`  (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `device_type_id` int(11) NOT NULL,
  `point_index` int(11) NOT NULL,
  `point_type` enum('DI','DO','AI','AO') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `point_name` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `mode` enum('read','write') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'read',
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `unique_point`(`device_type_id`, `point_index`) USING BTREE,
  CONSTRAINT `device_type_points_ibfk_1` FOREIGN KEY (`device_type_id`) REFERENCES `device_types` (`id`) ON DELETE CASCADE ON UPDATE RESTRICT
) ENGINE = InnoDB AUTO_INCREMENT = 261 CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci COMMENT = '设备点位配置表' ROW_FORMAT = Dynamic;

SET FOREIGN_KEY_CHECKS = 1;
### 测试指令
python cleanup_db.py; python import_csv_data.py



 python sync_simulation.py --neo4j_uri "bolt://192.168.35.10:7687" --neo4j_user "neo4j" --neo4j_password "13701033228"
 python sync_simulation.py --neo4j_uri "bolt://192.168.35.10:7687" --neo4j_user "neo4j" --neo4j_password "13701033228"

 ### 设备标识符说明
         importer.close() 修改这个代码。我要从csv中获得Vertex。并提取 Function Location Device 和 Terminal。获得这些属性是基于 = + - : 四种标志来获得属性。如果没有标记=+-:，则默认再字符串前这四种，然后拆分。如果没有:  则在最后一个-后边增加:   。然后进行属性处理，=与第一个+之间，是Function； 第一个+ 与第一个 - 之间，是Location； 第一个 - 与第一个: 之间，是Device；第一个:之后，是Terminal；