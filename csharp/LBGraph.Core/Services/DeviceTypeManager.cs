using System;
using System.Collections.Generic;
using System.Linq;
using LBGraph.Core.Models;

namespace LBGraph.Core.Services
{
    public class DeviceTypeManager
    {
        private readonly Dictionary<string, DeviceType> _deviceTypes;

        public DeviceTypeManager()
        {
            _deviceTypes = new Dictionary<string, DeviceType>
            {
                ["EDB"] = new DeviceType
                {
                    Id = "EDB",
                    Name = "增强模块 EDB",
                    PointCount = 20,
                    Description = "20点（7DI + 3DO + 10DI）",
                    InputPoints = Enumerable.Range(1, 17).Select(i => $"D{i}").ToList(),
                    OutputPoints = Enumerable.Range(1, 3).Select(i => $"B{i}").ToList()
                },
                ["EBD"] = new DeviceType
                {
                    Id = "EBD",
                    Name = "增强模块 EBD",
                    PointCount = 20,
                    Description = "20点（8DO + 4DI + 8DO）",
                    InputPoints = Enumerable.Range(1, 4).Select(i => $"D{i}").ToList(),
                    OutputPoints = Enumerable.Range(1, 16).Select(i => $"B{i}").ToList()
                },
                ["PDI"] = new DeviceType
                {
                    Id = "PDI",
                    Name = "PLC模块 PDI",
                    PointCount = 16,
                    Description = "16点（16DI）",
                    InputPoints = Enumerable.Range(1, 16)
                        .SelectMany(i => new[] { $"DI{i}", $"D{i}" })
                        .ToList(),
                    OutputPoints = new List<string>()
                },
                ["PDO"] = new DeviceType
                {
                    Id = "PDO",
                    Name = "PLC模块 PDO",
                    PointCount = 16,
                    Description = "16点（16DO）",
                    InputPoints = new List<string>(),
                    OutputPoints = Enumerable.Range(1, 16)
                        .SelectMany(i => new[] { $"DO{i}", $"B{i}" })
                        .ToList()
                },
                ["PAI"] = new DeviceType
                {
                    Id = "PAI",
                    Name = "PLC模块 PAI",
                    PointCount = 16,
                    Description = "16点（16AI）",
                    InputPoints = Enumerable.Range(1, 16).Select(i => $"AI{i}").ToList(),
                    OutputPoints = new List<string>()
                },
                ["PAO"] = new DeviceType
                {
                    Id = "PAO",
                    Name = "PLC模块 PAO",
                    PointCount = 16,
                    Description = "16点（16AO）",
                    InputPoints = new List<string>(),
                    OutputPoints = Enumerable.Range(1, 16).Select(i => $"AO{i}").ToList()
                },
                ["HI"] = new DeviceType
                {
                    Id = "HI",
                    Name = "人工模块 HI",
                    PointCount = 20,
                    Description = "20点（20AI）",
                    InputPoints = Enumerable.Range(1, 20).Select(i => $"AI{i}").ToList(),
                    OutputPoints = new List<string>()
                },
                ["HO"] = new DeviceType
                {
                    Id = "HO",
                    Name = "人工模块 HO",
                    PointCount = 20,
                    Description = "20点（20AO）",
                    InputPoints = new List<string>(),
                    OutputPoints = Enumerable.Range(1, 20).Select(i => $"AO{i}").ToList()
                }
            };
        }

        public DeviceType GetDeviceType(string deviceId)
        {
            if (!_deviceTypes.TryGetValue(deviceId, out var deviceType))
            {
                throw new ArgumentException($"未知的设备类型: {deviceId}");
            }
            return deviceType;
        }

        public IEnumerable<DeviceType> GetAllDeviceTypes()
        {
            return _deviceTypes.Values;
        }

        public bool IsValidDeviceType(string deviceId)
        {
            return _deviceTypes.ContainsKey(deviceId);
        }

        public void RegisterDeviceType(DeviceType deviceType)
        {
            if (string.IsNullOrWhiteSpace(deviceType.Id))
            {
                throw new ArgumentException("设备类型ID不能为空");
            }

            _deviceTypes[deviceType.Id] = deviceType;
        }
    }
}