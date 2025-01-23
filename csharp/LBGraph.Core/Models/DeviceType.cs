using System.Collections.Generic;

namespace LBGraph.Core.Models
{
    public class DeviceType
    {
        public string Id { get; set; }
        public string Name { get; set; }
        public int PointCount { get; set; }
        public string Description { get; set; }
        public List<string> InputPoints { get; set; }
        public List<string> OutputPoints { get; set; }
        public Dictionary<string, object> Properties { get; set; }

        public DeviceType()
        {
            InputPoints = new List<string>();
            OutputPoints = new List<string>();
            Properties = new Dictionary<string, object>();
        }

        public DeviceType(string id, string name, int pointCount, string description)
            : this()
        {
            Id = id;
            Name = name;
            PointCount = pointCount;
            Description = description;
        }
    }
}