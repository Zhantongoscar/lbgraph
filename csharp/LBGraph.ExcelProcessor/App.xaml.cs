using System.Windows;
using Microsoft.Extensions.DependencyInjection;
using LBGraph.ExcelProcessor.Services;
using LBGraph.ExcelProcessor.Views;
using LBGraph.ExcelProcessor.ViewModels;

namespace LBGraph.ExcelProcessor
{
    public partial class App : Application
    {
        private ServiceProvider _serviceProvider;

        public App()
        {
            ServiceCollection services = new ServiceCollection();
            ConfigureServices(services);
            _serviceProvider = services.BuildServiceProvider();
        }

        private void ConfigureServices(ServiceCollection services)
        {
            // 注册服务
            services.AddSingleton<ExcelProcessorService>();
            
            // 注册视图模型
            services.AddTransient<MainViewModel>();
            
            // 注册主窗口
            services.AddTransient<MainWindow>();
        }

        protected override void OnStartup(StartupEventArgs e)
        {
            base.OnStartup(e);

            var mainWindow = _serviceProvider.GetRequiredService<MainWindow>();
            mainWindow.Show();
        }

        protected override void OnExit(ExitEventArgs e)
        {
            base.OnExit(e);
            _serviceProvider?.Dispose();
        }
    }
}