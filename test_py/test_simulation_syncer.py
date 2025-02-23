import unittest
import logging
from unittest.mock import Mock, patch
import json
from c4_import_mysql_sim import SimulationSyncer

class TestSimulationSyncer(unittest.TestCase):
    def setUp(self):
        # 禁用日志输出
        logging.disable(logging.CRITICAL)
        
        # 测试数据
        self.test_device_types = [
            {'id': 1, 'type_name': 'TestType1'},
            {'id': 2, 'type_name': 'TestType2'}
        ]
        
        self.test_devices = [
            {'id': 1, 'type_id': 1, 'project_name': 'Test', 'module_type': 'A'},
            {'id': 2, 'type_id': 2, 'project_name': 'Test', 'module_type': 'B'}
        ]
        
        self.test_points = [
            {'device_type_id': 1, 'point_type': 'DO', 'point_index': 1},
            {'device_type_id': 1, 'point_type': 'DI', 'point_index': 2},
            {'device_type_id': 2, 'point_type': 'DO', 'point_index': 1}
        ]

        # 新增面板连接测试数据
        self.test_panel_connections = [
            {
                'device_id': 1,
                'panel_id': 'P1',
                'connections': json.dumps([
                    {"from": "21", "to": "22", "type": "contact_connection"},
                    {"from": "A1", "to": "A2", "type": "coil_connection"}
                ])
            }
        ]

    def test_data_validation_success(self):
        """测试数据验证成功的情况"""
        syncer = SimulationSyncer()
        # 不应该抛出异常
        syncer._validate_data(self.test_device_types, self.test_devices, self.test_points)

    def test_data_validation_invalid_type(self):
        """测试无效设备类型引用的情况"""
        syncer = SimulationSyncer()
        invalid_devices = [
            {'id': 1, 'type_id': 999, 'project_name': 'Test', 'module_type': 'A'}
        ]
        
        # 验证warning日志
        with self.assertLogs(level='WARNING') as log:
            syncer._validate_data(self.test_device_types, invalid_devices, self.test_points)
            self.assertIn('引用了不存在的设备类型', log.output[0])

    def test_process_panel_connections(self):
        """测试面板连接数据处理"""
        syncer = SimulationSyncer()
        processed = syncer.process_panel_connections(self.test_panel_connections)
        
        self.assertEqual(len(processed), 2)  # 应该有两个连接
        
        # 验证第一个连接（触点连接）
        self.assertEqual(processed[0]['from_terminal'], '21')
        self.assertEqual(processed[0]['to_terminal'], '22')
        self.assertEqual(processed[0]['connection_type'], 'contact_connection')
        
        # 验证第二个连接（线圈连接）
        self.assertEqual(processed[1]['from_terminal'], 'A1')
        self.assertEqual(processed[1]['to_terminal'], 'A2')
        self.assertEqual(processed[1]['connection_type'], 'coil_connection')

    def test_process_panel_connections_invalid_json(self):
        """测试处理无效JSON数据"""
        syncer = SimulationSyncer()
        invalid_connections = [
            {
                'device_id': 1,
                'panel_id': 'P1',
                'connections': 'invalid json'
            }
        ]
        
        # 验证错误日志
        with self.assertLogs(level='ERROR') as log:
            processed = syncer.process_panel_connections(invalid_connections)
            self.assertEqual(len(processed), 0)
            self.assertIn('解析连接数据时发生错误', log.output[0])

    @patch('neo4j.GraphDatabase.driver')
    @patch('pymysql.connect')
    def test_sync_process(self, mock_mysql, mock_neo4j):
        """测试同步过程"""
        # 设置MySQL mock
        mock_cursor = Mock()
        mock_cursor.fetchall.side_effect = [
            self.test_device_types,
            self.test_devices,
            self.test_points,
            self.test_panel_connections
        ]
        mock_mysql.return_value.cursor.return_value = mock_cursor
        
        # 设置Neo4j mock
        mock_session = Mock()
        mock_neo4j.return_value.session.return_value.__enter__.return_value = mock_session
        
        # 创建同步器实例
        syncer = SimulationSyncer()
        
        # 测试MySQL连接
        self.assertTrue(syncer.connect_mysql())
        
        # 测试数据获取
        device_types, devices, points, panel_connections = syncer.fetch_simulation_data()
        self.assertEqual(len(device_types), len(self.test_device_types))
        self.assertEqual(len(devices), len(self.test_devices))
        self.assertEqual(len(points), len(self.test_points))
        self.assertEqual(len(panel_connections), len(self.test_panel_connections))
        
        # 测试Neo4j同步
        syncer.sync_to_neo4j(device_types, devices, points, panel_connections)
        
        # 验证Neo4j操作
        self.assertTrue(mock_session.execute_write.called)
        self.assertTrue(mock_session.run.called)

    def tearDown(self):
        # 恢复日志输出
        logging.disable(logging.NOTSET)

if __name__ == '__main__':
    unittest.main()