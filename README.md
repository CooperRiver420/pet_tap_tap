# TapPet

PyQt6 桌面宠物程序。悬浮透明窗口 + 全局键盘战斗模式。

## 安装

```bash
git clone https://github.com/CooperRiver420/pet_tap_tap.git
cd pet_tap_tap
python3 -m venv .venv
source .venv/bin/activate    # Linux/macOS
# .venv\Scripts\activate     # Windows
pip install PyQt6 pynput
```

### Linux 额外依赖

```bash
sudo apt install python3-dev libevdev-dev
```

## 运行

```bash
python main.py
```

按 Ctrl+Shift+B 开启战斗。打字累计计数，0→10 次角色行走并刷新敌人，第 11 次起攻击，击杀后循环。

## 技术栈

Python 3.12 + PyQt6 + pynput

## License

MIT
