import unittest
import logging
from unittest.mock import Mock, patch
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

    @patch('neo4j.GraphDatabase.driver')
    @patch('pymysql.connect')
    def test_sync_process(self, mock_mysql, mock_neo4j):
        """测试同步过程"""
        # 设置MySQL mock
        mock_cursor = Mock()
        mock_cursor.fetchall.side_effect = [
            self.test_device_types,
            self.test_devices,
            self.test_points
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
        device_types, devices, points = syncer.fetch_simulation_data()
        self.assertEqual(len(device_types), len(self.test_device_types))
        self.assertEqual(len(devices), len(self.test_devices))
        self.assertEqual(len(points), len(self.test_points))
        
        # 测试Neo4j同步
        syncer.sync_to_neo4j(device_types, devices, points)
        
        # 验证Neo4j操作
        self.assertTrue(mock_session.execute_write.called)
        self.assertTrue(mock_session.run.called)

    def tearDown(self):
        # 恢复日志输出
        logging.disable(logging.NOTSET)

if __name__ == '__main__':
    unittest.main()