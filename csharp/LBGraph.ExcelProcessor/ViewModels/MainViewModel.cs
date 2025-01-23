using System;
using System.Collections.ObjectModel;
using System.ComponentModel;
using System.Runtime.CompilerServices;
using System.Windows.Input;
using Microsoft.Win32;
using LBGraph.ExcelProcessor.Services;
using System.Windows;

namespace LBGraph.ExcelProcessor.ViewModels
{
    public class MainViewModel : INotifyPropertyChanged
    {
        private readonly ExcelProcessorService _excelProcessor;
        private string _filePath;
        private ObservableCollection<object> _previewData;
        private ObservableCollection<KeyValuePair<string, string>> _columnMappings;

        public string FilePath
        {
            get => _filePath;
            set
            {
                _filePath = value;
                OnPropertyChanged();
            }
        }

        public ObservableCollection<object> PreviewData
        {
            get => _previewData;
            set
            {
                _previewData = value;
                OnPropertyChanged();
            }
        }

        public ObservableCollection<KeyValuePair<string, string>> ColumnMappings
        {
            get => _columnMappings;
            set
            {
                _columnMappings = value;
                OnPropertyChanged();
            }
        }

        public ICommand BrowseCommand { get; }
        public ICommand LoadDataCommand { get; }
        public ICommand ProcessDataCommand { get; }
        public ICommand SaveCommand { get; }

        public MainViewModel(ExcelProcessorService excelProcessor)
        {
            _excelProcessor = excelProcessor;
            
            // 初始化命令
            BrowseCommand = new RelayCommand(BrowseFile);
            LoadDataCommand = new RelayCommand(LoadData);
            ProcessDataCommand = new RelayCommand(ProcessData);
            SaveCommand = new RelayCommand(SaveData);

            // 初始化集合
            PreviewData = new ObservableCollection<object>();
            ColumnMappings = new ObservableCollection<KeyValuePair<string, string>>();
        }

        private void BrowseFile()
        {
            var dialog = new OpenFileDialog
            {
                Filter = "Excel文件|*.xlsx;*.xls",
                Title = "选择Excel文件"
            };

            if (dialog.ShowDialog() == true)
            {
                FilePath = dialog.FileName;
            }
        }

        private async void LoadData()
        {
            try
            {
                if (string.IsNullOrWhiteSpace(FilePath))
                {
                    MessageBox.Show("请先选择Excel文件", "提示", MessageBoxButton.OK, MessageBoxImage.Warning);
                    return;
                }

                await _excelProcessor.LoadExcelFileAsync(FilePath);
                UpdatePreviewData();
                UpdateColumnMappings();
            }
            catch (Exception ex)
            {
                MessageBox.Show($"加载数据失败：{ex.Message}", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private async void ProcessData()
        {
            try
            {
                var columnMapping = GetColumnMapping();
                var graphData = await _excelProcessor.ProcessToGraphDataAsync(columnMapping);
                var cleanedData = await _excelProcessor.CleanGraphDataAsync(graphData);
                UpdateProcessedDataPreview(cleanedData);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"处理数据失败：{ex.Message}", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private async void SaveData()
        {
            var dialog = new SaveFileDialog
            {
                Filter = "JSON文件|*.json",
                Title = "保存处理结果"
            };

            if (dialog.ShowDialog() == true)
            {
                try
                {
                    var fileName = System.IO.Path.GetFileNameWithoutExtension(dialog.FileName);
                    await _excelProcessor.SaveGraphDataAsync(_processedData, fileName);
                    MessageBox.Show("数据保存成功！", "成功", MessageBoxButton.OK, MessageBoxImage.Information);
                }
                catch (Exception ex)
                {
                    MessageBox.Show($"保存失败：{ex.Message}", "错误", MessageBoxButton.OK, MessageBoxImage.Error);
                }
            }
        }

        private void UpdatePreviewData()
        {
            // 更新预览数据
            PreviewData.Clear();
            var previewRows = _excelProcessor.GetPreviewData();
            foreach (var row in previewRows)
            {
                PreviewData.Add(row);
            }
        }

        private void UpdateColumnMappings()
        {
            // 更新列映射
            ColumnMappings.Clear();
            var mappings = _excelProcessor.SuggestColumnMapping();
            foreach (var mapping in mappings)
            {
                ColumnMappings.Add(new KeyValuePair<string, string>(mapping.Key, mapping.Value));
            }
        }

        private Dictionary<string, int> GetColumnMapping()
        {
            // 获取当前的列映射
            var mapping = new Dictionary<string, int>();
            foreach (var pair in ColumnMappings)
            {
                mapping[pair.Key] = _excelProcessor.GetColumnIndex(pair.Value);
            }
            return mapping;
        }

        private void UpdateProcessedDataPreview(Dictionary<string, object> data)
        {
            _processedData = data;
            // 可以在这里添加处理后数据的预览逻辑
        }

        private Dictionary<string, object> _processedData;

        public event PropertyChangedEventHandler PropertyChanged;
        protected virtual void OnPropertyChanged([CallerMemberName] string propertyName = null)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }
    }

    // 简单的命令实现
    public class RelayCommand : ICommand
    {
        private readonly Action _execute;
        private readonly Func<bool> _canExecute;

        public RelayCommand(Action execute, Func<bool> canExecute = null)
        {
            _execute = execute ?? throw new ArgumentNullException(nameof(execute));
            _canExecute = canExecute;
        }

        public event EventHandler CanExecuteChanged
        {
            add { CommandManager.RequerySuggested += value; }
            remove { CommandManager.RequerySuggested -= value; }
        }

        public bool CanExecute(object parameter)
        {
            return _canExecute?.Invoke() ?? true;
        }

        public void Execute(object parameter)
        {
            _execute();
        }
    }
}