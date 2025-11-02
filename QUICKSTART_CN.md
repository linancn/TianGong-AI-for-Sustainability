# 快速入门指南 — 一键配置

几分钟内运行 TianGong AI for Sustainability！

## 完全新手 👶

### macOS

1. **打开终端** 并进入项目文件夹：
   ```bash
   cd /path/to/TianGong-AI-for-Sustainability
   ```

2. **运行配置脚本：**
   ```bash
   bash install_macos.sh
   ```

3. **按照提示操作** — 脚本会询问您想要哪些可选功能：
   - 图表功能 (Node.js) ✓
   - PDF/DOCX 导出 (Pandoc + LaTeX) ✓
   - 碳排指标 (grid-intensity) ✓

4. **完成！** 安装后测试：
   ```bash
   uv run tiangong-research --help
   ```

### Ubuntu/Debian

1. **打开终端** 并进入项目文件夹：
   ```bash
   cd /path/to/TianGong-AI-for-Sustainability
   ```

2. **运行配置脚本：**
   ```bash
   bash install_ubuntu.sh
   ```

3. **按照提示操作** — 脚本会询问您想要哪些可选功能。

4. **完成！** 安装后测试：
   ```bash
   uv run tiangong-research --help
   ```

## 高级用户 🚀

### 预配置安装模式

**macOS — 完整安装（所有功能）：**
```bash
bash install_macos.sh --full
```

**macOS — 最小化（仅核心，无可选依赖）：**
```bash
bash install_macos.sh --minimal
```

**macOS — 指定功能安装：**
```bash
bash install_macos.sh --with-pdf --with-charts --with-carbon
```

**Ubuntu — 完整安装：**
```bash
bash install_ubuntu.sh --full
```

**Ubuntu — 最小化：**
```bash
bash install_ubuntu.sh --minimal
```

**Ubuntu — 指定功能安装：**
```bash
bash install_ubuntu.sh --with-pdf --with-charts --with-carbon
```

## 脚本做了什么 ✓

1. ✅ 安装 Python 3.12+（如需要）
2. ✅ 安装 `uv` 包管理器
3. ✅ 可选安装 Node.js、Pandoc、LaTeX
4. ✅ 克隆仓库（如需要）
5. ✅ 运行 `uv sync` 安装项目依赖
6. ✅ 验证所有组件是否正常工作
7. ✅ 提供 CLI 使用的后续步骤

## 下一步

配置完成后：

### 1. 列出可用数据源
```bash
uv run tiangong-research sources list
```

### 2. 测试特定数据源
```bash
uv run tiangong-research sources verify un_sdg_api
```

### 3. 运行您的第一个工作流
```bash
uv run tiangong-research research workflow simple --topic "生命周期评估"
```

### 4. 生成报告（如已安装 PDF 支持）
```bash
# 生成 Markdown 报告
uv run tiangong-research research workflow simple \
  --topic "可持续能源" \
  --report-output reports/output.md

# 用 Pandoc 转换为 PDF
pandoc reports/output.md -o reports/output.pdf
```

## 故障排除

### 安装后出现"命令未找到"

**macOS：**
```bash
source ~/.zshrc
```

**Ubuntu：**
```bash
source ~/.bashrc
```

### 脚本权限错误

```bash
chmod +x install_macos.sh
# 或
chmod +x install_ubuntu.sh
```

### 想查看脚本的具体操作

您可以在运行前查看脚本内容：
- **macOS**: `cat install_macos.sh`
- **Ubuntu**: `cat install_ubuntu.sh`

## 手动安装

如果您不想使用自动化脚本，请参考[详细安装指南](./SETUP_GUIDE_CN.md)。

## 获取帮助

- 📖 **用户指南**: [README_CN.md](./README_CN.md)
- 🔧 **详细配置**: [SETUP_GUIDE_CN.md](./SETUP_GUIDE_CN.md)
- 🏗️ **架构说明**: [specs/architecture_CN.md](./specs/architecture_CN.md)
- 🤖 **AI 智能体指南**: [AGENTS_CN.md](./AGENTS_CN.md)
