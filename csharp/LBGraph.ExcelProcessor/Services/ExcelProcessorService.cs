using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using OfficeOpenXml;
using Newtonsoft.Json;

namespace LBGraph.ExcelProcessor.Services
{
    public class ExcelProcessorService
    {
        private ExcelWorksheet _worksheet;
        private readonly Dictionary<string, string> _requiredColumns = new()
        {
            { "serial", "Consecutive number" },
            { "color", "Connection color / number" },
            { "source", "Device (source)" },
            { "target", "Device (target)" }
        };

        public ExcelProcessorService()
        {
            // 设置EPPlus许可模式
            ExcelPackage.LicenseContext = LicenseContext.NonCommercial;
        }

        public async Task LoadExcelFileAsync(string filePath, int? rowCount = null)
        {
            if (!File.Exists(filePath))
                throw new FileNotFoundException($"文件不存在: {filePath}");

            using var package = new ExcelPackage(new FileInfo(filePath));
            _worksheet = package.Workbook.Worksheets[0];

            if (rowCount.HasValue && (rowCount.Value <= 0 || rowCount.Value > _worksheet.Dimension.Rows))
                throw new ArgumentException("指定的行数超出范围");
        }

        public List<object> GetPreviewData(int previewRows = 10)
        {
            if (_worksheet == null)
                throw new InvalidOperationException("请先加载Excel文件");

            var result = new List<object>();
            var headers = GetColumns().ToList();
            
            for (int row = 2; row <= Math.Min(_worksheet.Dimension.Rows, previewRows + 1); row++)
            {
                var rowData = new Dictionary<string, string>();
                for (int col = 1; col <= headers.Count; col++)
                {
                    rowData[headers[col - 1]] = _worksheet.Cells[row, col].Text;
                }
                result.Add(rowData);
            }

            return result;
        }

        public IEnumerable<string> GetColumns()
        {
            if (_worksheet == null)
                throw new InvalidOperationException("请先加载Excel文件");

            return Enumerable.Range(1, _worksheet.Dimension.Columns)
                .Select(col => _worksheet.Cells[1, col].Text)
                .Where(header => !string.IsNullOrEmpty(header));
        }

        public Dictionary<string, string> SuggestColumnMapping()
        {
            var columns = GetColumns().ToList();
            var mapping = new Dictionary<string, string>();

            foreach (var (key, value) in _requiredColumns)
            {
                var suggestion = columns
                    .FirstOrDefault(x => x.Contains(value, StringComparison.OrdinalIgnoreCase));

                if (suggestion != null)
                {
                    mapping[key] = suggestion;
                }
            }

            return mapping;
        }

        public int GetColumnIndex(string columnName)
        {
            var columns = GetColumns().ToList();
            return columns.IndexOf(columnName) + 1;
        }

        private Dictionary<string, string> ParseIECIdentifier(string identifier)
        {
            var result = new Dictionary<string, string>
            {
                { "function", "" },
                { "location", "" },
                { "device", "" },
                { "terminal", "" }
            };

            var pattern = @"=(?<function>[^+]*)\+(?<location>[^-]*)-(?<device>[^:]*):(?<terminal>.*)";
            var match = Regex.Match(identifier, pattern);

            if (!match.Success)
            {
                // 尝试提取location
                var locationMatch = Regex.Match(identifier, @"K1\.\d{2}");
                if (locationMatch.Success)
                {
                    result["location"] = locationMatch.Value;
                }
                return result;
            }

            result["function"] = match.Groups["function"].Value;
            result["location"] = match.Groups["location"].Value;
            result["device"] = match.Groups["device"].Value;
            result["terminal"] = match.Groups["terminal"].Value;

            return result;
        }

        public async Task<Dictionary<string, object>> ProcessToGraphDataAsync(Dictionary<string, int> columnMapping)
        {
            if (_worksheet == null)
                throw new InvalidOperationException("请先加载Excel文件");

            var graphData = new Dictionary<string, object>
            {
                ["nodes"] = new List<Dictionary<string, object>>(),
                ["edges"] = new List<Dictionary<string, object>>(),
                ["metadata"] = new Dictionary<string, object>
                {
                    ["created_at"] = DateTime.UtcNow.ToString("o"),
                    ["version"] = "1.0"
                }
            };

            var nodes = new HashSet<string>();
            var nodesList = (List<Dictionary<string, object>>)graphData["nodes"];
            var edgesList = (List<Dictionary<string, object>>)graphData["edges"];

            for (int row = 2; row <= _worksheet.Dimension.Rows; row++)
            {
                var source = _worksheet.Cells[row, columnMapping["source"]].Text;
                var target = _worksheet.Cells[row, columnMapping["target"]].Text;

                // 添加节点
                foreach (var node in new[] { source, target })
                {
                    if (!string.IsNullOrEmpty(node) && nodes.Add(node))
                    {
                        var nodeInfo = ParseIECIdentifier(node);
                        nodesList.Add(new Dictionary<string, object>
                        {
                            ["id"] = node,
                            ["iec_identifier"] = node,
                            ["properties"] = nodeInfo
                        });
                    }
                }

                // 添加边
                if (!string.IsNullOrEmpty(source) && !string.IsNullOrEmpty(target))
                {
                    edgesList.Add(new Dictionary<string, object>
                    {
                        ["source"] = source,
                        ["target"] = target,
                        ["properties"] = new Dictionary<string, object>
                        {
                            ["color"] = _worksheet.Cells[row, columnMapping["color"]].Text,
                            ["serial_number"] = _worksheet.Cells[row, columnMapping["serial"]].Text
                        }
                    });
                }
            }

            return graphData;
        }

        public async Task<Dictionary<string, object>> CleanGraphDataAsync(Dictionary<string, object> graphData)
        {
            var nodes = (List<Dictionary<string, object>>)graphData["nodes"];
            var edges = (List<Dictionary<string, object>>)graphData["edges"];
            var validEdges = new List<Dictionary<string, object>>();

            foreach (var edge in edges)
            {
                var sourceNode = nodes.FirstOrDefault(n => n["id"].ToString() == edge["source"].ToString());
                var targetNode = nodes.FirstOrDefault(n => n["id"].ToString() == edge["target"].ToString());

                var sourceProperties = (Dictionary<string, string>)sourceNode?["properties"];
                var targetProperties = (Dictionary<string, string>)targetNode?["properties"];

                bool sourceValid = sourceProperties != null && 
                    Regex.IsMatch(sourceProperties["location"], @"K1\.*");
                bool targetValid = targetProperties != null && 
                    Regex.IsMatch(targetProperties["location"], @"K1\.*");

                if (sourceValid && targetValid)
                {
                    validEdges.Add(edge);
                }
            }

            graphData["edges"] = validEdges;
            return graphData;
        }

        public async Task SaveGraphDataAsync(Dictionary<string, object> graphData, string fileName)
        {
            var outputPath = Path.Combine("output", $"{fileName}.json");
            Directory.CreateDirectory(Path.GetDirectoryName(outputPath));

            await File.WriteAllTextAsync(
                outputPath,
                JsonConvert.SerializeObject(graphData, Formatting.Indented)
            );
        }
    }
}