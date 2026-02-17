# Notion 图表嵌入说明

## 概述

现在系统支持将生成的图表**直接嵌入**到 Notion 页面中，而不是仅显示文件路径。

## 工作原理

1. 系统生成图表（PNG格式）保存到本地
2. 图表上传到 **Imgur 图床**（免费）获取公开 URL
3. 使用 Notion 的 `external` image block 嵌入图片
4. 图片永久显示在 Notion 页面中

## 配置步骤

### 1. 申请 Imgur Client ID（免费）

1. 访问 https://api.imgur.com/oauth2/addclient
2. 填写申请信息：
   - **Application name**: `Stock Monitor`（任意）
   - **Authorization type**: 选择 `OAuth 2 authorization without a callback URL`
   - **Website**: 可留空或填 `http://localhost`
   - **Email**: 你的邮箱
3. 提交后获得 **Client ID**（类似 `a1b2c3d4e5f6g7h`）

### 2. 配置到项目

编辑 `.env` 文件，添加：

```bash
IMGUR_CLIENT_ID=你的_client_id_here
```

### 3. 运行监控

```bash
python3 main.py --run-once
```

运行后，Notion 页面将显示嵌入的图表：

```
📊 关键指标时间序列图

TOP板块资金流向趋势
[图表图片直接显示在这里]
```

## 效果对比

### 不配置 Imgur（之前）
```
📊 关键指标时间序列图

⚠️ 图表文件: charts/top_sectors_trend_xxx.png
   请查看本地文件系统中的图表。
```

### 配置 Imgur 后（现在）
```
📊 关键指标时间序列图

[图片直接显示在Notion中]
```

## 费用说明

- **Imgur**: 免费，有每日上传限制（约 50 张/小时，足够使用）
- **图片保留**: 只要不手动删除，Imgur 图片永久有效

## 隐私说明

- 图表上传到 Imgur 后是**公开访问**的
- 如果图表包含敏感信息，建议：
  1. 不配置 Imgur，仅使用本地文件
  2. 或使用私有图床服务

## 故障排除

### 图片没有嵌入
检查日志：
```
Imgur连接测试失败
```
→ 检查 Client ID 是否正确

### 上传失败
```
上传请求失败
```
→ 可能达到 Imgur 限制，等待一段时间重试

## 替代方案

如果不想使用 Imgur，可以：
1. 使用其他图床服务（需要修改 `image_uploader.py`）
2. 使用 AWS S3 / 阿里云 OSS 等对象存储
3. 保持现状，手动查看本地图表文件

## 技术细节

- 图片格式: PNG
- 上传方式: Base64 编码后 POST 到 Imgur API
- Notion 嵌入: 使用 `external` 类型的 image block
