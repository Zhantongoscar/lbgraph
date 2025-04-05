import pyvisa
from queue import Queue
from threading import Lock
import time

class PowerSupplyController:
    """程控电源控制器 (SCPI协议)"""
    
    def __init__(self, resource_name):
        self.rm = pyvisa.ResourceManager()
        self.device = None
        self.resource_name = resource_name
        self.command_queue = Queue()
        self.lock = Lock()
        self.voltage_cache = {}
        
        # 安全参数
        self.MAX_VOLTAGE = 30.0
        self.MAX_CURRENT = 5.0
        
    def connect(self):
        """建立安全连接"""
        try:
            with self.lock:
                self.device = self.rm.open_resource(self.resource_name)
                self.device.timeout = 5000  # 5秒超时
                idn = self.device.query('*IDN?').strip()
                
                # 验证设备型号
                if 'Agilent' not in idn and 'Keysight' not in idn:
                    raise ValueError("不支持的电源型号")
                    
                # 初始化安全设置
                self._send_command(f"APPLY 0,{self.MAX_CURRENT}")  # 初始0V
                self._send_command("OUTP OFF")
                print(f"已连接电源设备: {idn}")
                return True
                
        except pyvisa.VisaIOError as e:
            print(f"连接失败: {str(e)}")
            return False

    def set_voltage(self, voltage, current_limit=None):
        """设置输出电压和电流限制"""
        if not 0 <= voltage <= self.MAX_VOLTAGE:
            raise ValueError(f"电压值超出安全范围(0-{self.MAX_VOLTAGE}V)")
            
        current = current_limit or self.MAX_CURRENT
        with self.lock:
            self._send_command(f"APPLY {voltage},{current}")
            self.voltage_cache['set'] = voltage
            time.sleep(0.5)  # 等待电压稳定

    def enable_output(self, enable=True):
        """启用/禁用电源输出"""
        state = "ON" if enable else "OFF"
        with self.lock:
            self._send_command(f"OUTP {state}")
            if enable:
                self._safety_check()

    def _safety_check(self):
        """执行安全自检"""
        actual_voltage = self.read_actual_voltage()
        if abs(actual_voltage - self.voltage_cache.get('set', 0)) > 1.0:
            self.enable_output(False)
            raise RuntimeError("输出电压与设定值偏差过大")

    def read_actual_voltage(self):
        """读取实际输出电压"""
        with self.lock:
            response = self._send_query("MEAS:VOLT?")
            return float(response)

    def _send_command(self, command):
        """安全发送命令"""
        try:
            self.device.write(command)
        except pyvisa.VisaIOError as e:
            self.enable_output(False)
            raise RuntimeError(f"命令发送失败: {command}") from e

    def _send_query(self, query):
        """安全发送查询"""
        try:
            return self.device.query(query).strip()
        except pyvisa.VisaIOError as e:
            self.enable_output(False)
            raise RuntimeError(f"查询失败: {query}") from e

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.enable_output(False)
        self.device.close()
        print("电源连接已安全关闭")

if __name__ == "__main__":
    # 示例用法
    with PowerSupplyController("TCPIP0::192.168.1.100::inst0::INSTR") as ps:
        ps.set_voltage(24.0, 1.0)
        ps.enable_output()
        print(f"当前电压: {ps.read_actual_voltage()}V")
        ps.enable_output(False)