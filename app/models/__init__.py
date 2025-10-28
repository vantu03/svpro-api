import importlib
import pkgutil
import pathlib

# Tự động import tất cả file Python trong thư mục models
package_dir = pathlib.Path(__file__).parent
for module in pkgutil.iter_modules([str(package_dir)]):
    importlib.import_module(f"{__name__}.{module.name}")
