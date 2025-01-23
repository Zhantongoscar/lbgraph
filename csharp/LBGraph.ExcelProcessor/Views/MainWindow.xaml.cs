using System.Windows;
using LBGraph.ExcelProcessor.Services;

namespace LBGraph.ExcelProcessor.Views
{
    public partial class MainWindow : Window
    {
        private readonly ExcelProcessorService _excelProcessor;

        public MainWindow(ExcelProcessorService excelProcessor)
        {
            InitializeComponent();
            _excelProcessor = excelProcessor;
            
            // 设置数据上下文
            DataContext = new ViewModels.MainViewModel(_excelProcessor);
        }
    }
}