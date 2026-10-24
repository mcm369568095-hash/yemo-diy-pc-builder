# 夜秣万能DIY装机顾问 · 按量付费（A2M 402）接口契约

面向**调用方**（Agent / 脚本），不是商家服务端。签名、验付、履约确认均在服务端完成，
调用方只负责发请求、读账单、带凭证重试、校验交付证据。

## 一、资源与价格

| 项 | 值 |
| :--- | :--- |
| 资源地址 | `https://api.yemo.xyz/api/diy/build` |
| 请求方式 | GET（query）或 POST（JSON body），同一路径 |
| 单次价格 | **4.90 元 / 次**（人民币） |
| 商品名 | 夜秣DIY装机顾问·单次配置方案 |
| 服务号 | `API_XXXXXXXXXXXXXXXX（DIY 服务号）` |
| 商户 PID | `2088XXXXXXXXXXXX（你的商户 PID）` |
| 计费方式 | 按次，与支付宝服务市场登记单价一致 |

## 二、请求参数

| 参数 | 类型 | 必填 | 说明 |
| :--- | :--- | :--- | :--- |
| `budget` | number | 否 | 预算（元）。给了才输出预算分配矩阵与二手等效换算 |
| `usage` | string | 否 | 用途：游戏 / AI绘图 / 剪辑 / 办公 / 家用 |
| `game` | string | 否 | 游戏名（触发分辨率矩阵） |
| `resolution` | string | 否 | 1080p / 2K / 4K |
| `cpu` | string | 否 | 指定 CPU 型号（触发插槽校验） |
| `gpu` | string | 否 | 指定显卡型号 |
| `mainboard` | string | 否 | 指定主板型号（与 cpu 联合校验跨家混用） |
| `case_size` | string | 否 | ATX / M-ATX / ITX |
| `pref` | string | 否 | 全新 / 二手 / 双方案 |

请求示例：

```json
{"budget":6000,"usage":"游戏","game":"黑神话 悟空","resolution":"2K"}
```

## 三、402 账单

无 `Payment-Proof` 请求头时返回 **HTTP 402**，响应头携带
`Payment-Needed: <base64url(JSON)>`，结构：

```json
{
  "protocol": {
    "out_trade_no": "YEMO...",
    "amount": "4.90",
    "currency": "CNY",
    "resource_id": "/api/diy/build",
    "pay_before": "2026-09-23T21:58:23+08:00",
    "seller_signature": "...",
    "seller_sign_type": "RSA2",
    "seller_unique_id": "2088XXXXXXXXXXXX（你的商户 PID）"
  },
  "method": {
    "seller_name": "夜秣PPT工坊",
    "seller_id": "2088XXXXXXXXXXXX（你的商户 PID）",
    "seller_app_id": "2021XXXXXXXXXXXX（你的 AppID）",
    "goods_name": "夜秣DIY装机顾问·单次配置方案",
    "seller_unique_id_key": "seller_id",
    "service_id": "API_XXXXXXXXXXXXXXXX（DIY 服务号）"
  }
}
```

响应体：`{"code":"Payment-Needed","amount":"4.90","out_trade_no":"...","goods_name":"..."}`。
`pay_before` 默认 30 分钟有效。

## 四、带凭证重试与交付

付款完成后，调用方携带 `Payment-Proof: <base64url>` 请求头，**用同一订单号重试同一请求**：

- **200**：交付成功。响应体含 `resource_id` / `content` / `trade_no` / `out_trade_no` /
  `already_fulfilled` / `fulfillment_confirmed`；响应头含 `Payment-Validation`。
- **502 `FULFILLMENT_CONFIRM_FAILED`**：资源可能已生成，但履约确认失败。
  **用同一凭证重试，不重新付款**。
- **402**：凭证无效或未完成支付，需重新走付款流程。

交付内容 `content` 字段：

| 字段 | 说明 |
| :--- | :--- |
| `scene` | 场景判定：游戏优先 / 生产力优先 / 办公家用 |
| `budget` / `used_equivalent` | 预算与二手等效换算（÷ 0.68） |
| `allocation[]` | 预算分配矩阵：部件 / 占比 / 全新行货预算 / 二手参考 |
| `compatibility` | 插槽兼容性校验结果，`violation` 非空即跨家混用 |
| `request` | 入参回执 |
| `artifact` | 落盘的 Markdown 方案单（文件名 / 字节数） |

Markdown 方案单下载：`GET https://api.yemo.xyz/api/diy/download/{out_trade_no}`

## 五、铁律

1. **支付职责分工**：账单签名、验付（`payment.verify`）与商家履约确认（`fulfillment.confirm`）
   由商家服务端（api.yemo.xyz）实现；技能端脚本只做编排——发请求、解析 402 账单、
   状态持久化、携凭证重试，付款始终走支付宝官方收银流程。
2. **复用同一订单号**：付款后重试必须带原 `out_trade_no`，重复请求不重复扣费。
3. **状态不明先查单**：`GET /api/diy/download/{out_trade_no}`，200 即已交付。
4. **成功路径不追加独立回执**：200 + `Payment-Validation` 即为交付证据。
5. **未经确认不发起真实付款**：生产付款停在人工确认前。

## 六、服务端边界说明

服务端只做三件可验证的事：需求回执、预算分配演算、插槽兼容性硬校验，并落盘方案单。
**具体型号与实时行情由调用方技能按其规则库填充，服务端不臆造型号与报价。**
