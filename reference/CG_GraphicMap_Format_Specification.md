# 魔力宝贝(CrossGate) 文件结构与解析规范

本文档是为 AI 助手及开发人员准备的魔力宝贝（CrossGate）客户端文件（图像、地图等）解析规范。文档基于逆向工程提供详细的文件二进制结构和解码算法，以便于 AI 可以直接依据本规范精准编写数据提取、解析和渲染的代码。

## 1. 系统架构与文件关联概述

魔力宝贝的客户端资源主要存储在二进制文件中：
- **`GraphicInfo*_*.bin`**: 图像索引文件。提供每张图片的编号、在数据大文件中的偏移量(Offset)、大小及坐标偏移。
- **`Graphic*_*.bin`**: 图像数据文件。存储经过 Run-Length 压缩的图片像素数据及标头信息。
- **`palet_*.cgp`**: 全局调色板文件（主要应用于早期版本，如神兽传奇、魔弓传奇、龙之沙漏）。
- **`map/*.dat`**: 地图文件。记录地面的地块拼接、地表物件、碰撞和传送点信息。
- **乐园之卵(PUK2)及以后版本**: 引入了自带调色板的图片格式以及地图图块分割文件 (`*.cut`)。

---

## 2. 图像解析 (Graphics)

### 2.1 图像索引文件 (`GraphicInfo*_*.bin`)

每个索引记录固定长度为 **40 Bytes**。

**C/C++ 结构体定义：**
```cpp
#pragma pack(push, 1)
struct GraphicInfoRecord {
    uint32_t mapNumber;      // 地图编号 (0 代表一般物件/人物/宠物等，大于0为地图专用图块)
    uint32_t graphicNumber;  // 图像编号 (唯一ID)
    uint32_t addressOffset;  // 图像数据在对应的 Graphic*_*.bin 中的绝对字节偏移量
    uint32_t dataLength;     // 图像数据的字节长度 (包含标头)
    int32_t  offsetX;        // 绘制时的 X 偏移量
    int32_t  offsetY;        // 绘制时的 Y 偏移量
    uint32_t width;          // 图像宽度
    uint32_t height;         // 图像高度
    uint8_t  unknown[8];     // 未知数据，通常填充为 0
};
#pragma pack(pop)
```
*注：在 1.0 至 3.0 (龙之沙漏) 中，所有地面图像的尺寸固定为 64x47，`offsetX` = -32，`offsetY` = -24。*

### 2.2 图像数据文件 (`Graphic*_*.bin`)

通过索引记录的 `addressOffset` 来读取，每个数据块由“标头”+“压缩数据”组成。

#### 早期版本标头 (神兽传奇 / 魔弓传奇 / 龙之沙漏)

长度为 **16 Bytes**。

**C/C++ 结构体定义：**
```cpp
#pragma pack(push, 1)
struct GraphicHeaderV1 {
    char     signature[2]; // 固定为 'R', 'D'
    uint8_t  version;      // 0 或 2: 未压缩位图数据; 1: 已压缩数据 (Run-Length)
    uint8_t  unknown;      
    uint32_t width;        // 宽度
    uint32_t height;       // 高度
    uint32_t dataLength;   // 数据块总长度(包含此16字节标头，故压缩数据实际长度为 dataLength - 16)
};
#pragma pack(pop)
```

#### PUK2 (乐园之卵) 及以后版本标头

自 PUK2 开始，图像采用自带调色板格式，标头长度扩展为 **20 Bytes**。

**C/C++ 结构体定义：**
```cpp
#pragma pack(push, 1)
struct GraphicHeaderV2 {
    char     signature[2]; // 固定为 'R', 'D'
    uint8_t  version;      // 3 代表乐园之卵版本(已压缩 + 自带调色板)
    uint8_t  unknown;
    uint32_t width;        // 宽度
    uint32_t height;       // 高度
    uint32_t dataLength;   // 数据块总长度
    uint32_t paletteLength;// 自带调色板长度，通常为 768 Bytes (256种颜色 * 3通道 BGR)
};
#pragma pack(pop)
```
*解压策略：PUK2 中，先读取 20 字节标头，再读取压缩数据进行解压。解压后的原始数据包含两部分：前面是像素索引数据，紧随其后的是大小为 `paletteLength` 的局部调色板数据。*

### 2.3 Run-Length 解压算法 (RLD)

魔力宝贝图像使用特有的 Run-Length 解压缩方法。读取压缩数据流的每个指令字节（`Opcode`），根据其高位半字节（High Nibble）决定操作。

**指令集解析逻辑：**
- 设从压缩数据流中读取的字节为 `Opcode`。
- **`0x00 ~ 0x0F` (高位 0)**：接下来读取 1 个字节 `x`。从数据流拷贝接下来的 `x` 个字节的原生数据到输出缓冲区。
- **`0x10 ~ 0x1F` (高位 1)**：接下来读取 1 个字节 `yy`。计算数量 `count = ((Opcode & 0x0F) << 8) | yy`。从数据流拷贝接下来的 `count` 个字节原生数据到输出缓冲区。
- **`0x80 ~ 0x8F` (高位 8)**：接下来读取 1 个字节 `yy` (颜色索引)。将颜色索引 `yy` 重复写入输出缓冲区，次数为 `count = (Opcode & 0x0F)`。
- **`0x90 ~ 0x9F` (高位 9)**：接下来读取 2 个字节 `yy` (颜色索引) 和 `zz` (数量低位)。计算数量 `count = ((Opcode & 0x0F) << 8) | zz`。将颜色索引 `yy` 重复写入输出缓冲区 `count` 次。
- **`0xC0 ~ 0xCF` (高位 C)**：将“透明色”(Transparent Color) 重复写入输出缓冲区，次数为 `count = (Opcode & 0x0F)`。
- **`0xD0 ~ 0xDF` (高位 D)**：接下来读取 1 个字节 `yy`。计算数量 `count = ((Opcode & 0x0F) << 8) | yy`。将“透明色”重复写入输出缓冲区 `count` 次。

**渲染方向注意事项：**
解压后得到的二维像素缓冲区不能按常规的“左上至右下”顺序绘制。它采用类似 BMP 格式的“自底向上”(Bottom-Up) 存储方式。开发代码时，必须从左到右，从底行向顶行（Bottom to Top）逐行填充像素，否则渲染出的图像会上下倒置。

### 2.4 全局调色板文件 (`palet_*.cgp`)

对于没有自带调色板的早期图片（Version 1），需使用全局调色板将像素索引转换为 RGB 颜色。
- 文件大小固定为 **708 Bytes**。
- 存储了 236 种颜色 (236 * 3 = 708)，以 **B, G, R** 顺序存储每种颜色。
- 魔力宝贝调色板空间共有 256 个索引。其中索引 `0~15` 和 `240~255` 是客户端预设的系统保留色（需代码硬编码默认色板）。
- `palet_*.cgp` 提供的是索引 `16` 到 `251` 的颜色映射（实际游戏多使用 16~239）。
- **颜色查找算法：** 假设解压后的像素值为 `index`。
  - 若 `16 <= index < 252`，在 `.cgp` 文件中读取绝对偏移量 `(index - 16) * 3` 处的 3 个字节（BGR）。
  - 若超出此范围（例如 < 16 或 >= 252），应使用预设的系统标准调色板颜色。

常用的调色板文件名包括：白天 `palet_00.cgp`, 傍晚 `palet_01.cgp`, 晚上 `palet_02.cgp`, 凌晨 `palet_03.cgp`, 部分室内 `palet_12.cgp`。

---

## 3. 地图解析 (`map/*.dat`)

### 3.1 地图文件结构

每张 `.dat` 地图文件分为四大区块，按顺序连续排列：

1. **标头 (20 Bytes)**
   - `char magic[3]`: 固定字符为 "MAP"
   - `uint8_t padding[9]`: 全零或空白填充
   - `uint32_t width`: 地图格数宽度 (W)
   - `uint32_t height`: 地图格数高度 (H)
2. **地面数据区块 (W * H * 2 Bytes)**
   - 每 2 Bytes (WORD, Little-Endian) 构成一个地面图块编号。
3. **地上物件/建筑数据区块 (W * H * 2 Bytes)**
   - 每 2 Bytes (WORD, Little-Endian) 构成一个物件/建筑图块编号。
4. **地图标志/碰撞区块 (W * H * 2 Bytes)**
   - 每 2 Bytes 为一组属性标记：
     - Byte 1: `0` 或 `10`。 (`10` 表示该格可触发场景转换/传送)。
     - Byte 2: `0` (无地图), `192` (可通行), `193` (不可穿越/碰撞体)。
     - 代码解析时，组合成 unsigned short 的十进制数值常见为：`0`, `49152` (通行), `49162` (传送点), `49408` (阻挡)。

### 3.2 版本兼容性修正 (适用于神兽/魔弓/龙之沙漏等旧版)
由于旧版地图 `WORD` (2 Bytes) 的最大值限制，读取到地面与建筑的 WORD 编号后需进行逻辑修正映射：
- 若地面编号 `>= 20000`，实际指向的图块编号应为 `原编号 + 200000`。
- 建筑物编号在 `200 ~ 265` 区间均不需显示（视为透明空物件）。
- 若建筑物编号为 `25290` 或 `>= 30000`，实际指向的图块编号应为 `原编号 + 200000`。

### 3.3 地图绘制坐标 (Isometric 45度视角)
地图的渲染采用等距视角（菱形网格，Isometric Projection）。
基准坐标推导公式（以神兽传奇旧版图块尺寸 64x47 像素为例）：
- 给定网格坐标 `(w, h)`，地块的基础屏幕 `x` 坐标推算逻辑包含 `(w + h) * 32`。
- 建筑物在格子上的绘制 X 坐标基准约为: `(w + h) * 32 + 图像偏移量X + 96`。（具体实现需结合实际菱形平铺算法适当调校）。

---

## 4. PUK2 (乐园之卵) 及后续版本地图系统更新

在 PUK2 版本（地图编号 `> 50000`）之后，图像体系有所变化，引入了地图图块二次分割系统 (`*.cut`)。

### 4.1 分割文件 `Puk2/cutdat/*.cut`
地图 `*.dat` 中的图块编号不再直接对应 `GraphicInfo` 里的图片，而是作为索引，查找对应 `*.cut` 文件内的分割属性定义。
- **标头 (12 Bytes)**
  - `char magic[3]`: 固定为 "CUT"
  - `uint8_t unknown[7]`: 未知数据
  - `uint16_t blockCount`: 记录文件包含的数据块总数 (位于标头末尾2字节)
- **数据块 (每个 18 Bytes)**
  - `uint32_t mapNumber`: 指向的源大图编号 (用于从 GraphicInfo 读取对应大图)
  - `uint8_t unknown[2]`: 未知属性
  - `uint16_t sourceX`: 在源大图片上开始截取的左上角 X 坐标
  - `uint16_t sourceY`: 在源大图片上开始截取的左上角 Y 坐标
  - `uint16_t width`: 截取宽度
  - `uint16_t height`: 截取高度
  - `uint16_t offsetX`: 绘制时的偏移量 X
  - `uint16_t offsetY`: 绘制时的偏移量 Y

### 4.2 小地图文件 `Puk2/cutdat/*.Aut`
专门用于 3.0 类地图的快速小地图生成。
- 无标头。文件大小精确等于：`(对应的 .dat 地图文件大小 - 20) / 2`。
- 每 **3 Bytes** 为一个数据块，代表一个网格点的 `RGB` 颜色。
- 结合 `.dat` 文件中读取的宽 `W` 和高 `H`，可直接依次映射出小地图像素矩阵。

---

## 5. 其他关联附属文件

目前已知影响特定系统表现的文件结构：
- **`coordinate*.bin`**: 存储头饰系统等人物相关绘制偏移量，每 **8 Bytes** 为一个数据块。
- **`coordinateinfo*.bin`**: 头饰相关偏移的索引文件，每 **10 Bytes** 为一数据块。
  - `uint8_t unknown1`
  - `uint8_t unknown2`
  - `uint8_t fixed_1`: 固定为数值 1
  - `uint8_t fixed_0`: 固定为数值 0
  - `uint32_t address`: 指向 `coordinate*.bin` 的地址位置
  - `uint16_t blockCount`: 对应的数据块数量 (在 coordinate*.bin 中的 8字节块 个数)
