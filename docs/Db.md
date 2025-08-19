# 数据库表

## 表 1：Welcome
| 字段名          | 类型            | 说明        |
|--------------|---------------|-----------|
| `id`         | Integer（主键）   | 唯一标识      |
| `title`      | CharField     | 欢迎标题      |
| `image`      | ImageField    | 欢迎页图片文件路径 |
| `created_at` | DateTimeField | 创建时间      |

## 表 2：Banner
| 字段名          | 类型            | 说明        |
|--------------|---------------|-----------|
| `id`         | Integer（主键）   | 唯一标识      |
| `image`      | ImageField    | 轮播图图片路径   |
| `order`      | IntegerField  | 排序值，越大越靠前 |
| `created_at` | DateTimeField | 上传时间      |

## 表 3：canteen
| 字段名            | 类型           | 说明         |
|----------------|--------------|------------|
| id             | Integer (PK) | 主键 ID      |
| name           | Varchar(100) | 食堂名称       |
| location       | Varchar(255) | 食堂位置       |
| opening\_hours | Varchar(100) | 营业时间描述     |
| stall\_count   | Integer      | 档口数量       |
| image          | ImageField   | 食堂图片（存储路径） |

## 表 4：stall
| 字段名                  | 类型                    | 说明     |
|----------------------|-----------------------|--------|
| id                   | Integer (PK)          | 主键 ID  |
| name                 | Varchar(100)          | 档口名称   |
| cuisine\_type        | Varchar(100)          | 菜系类型   |
| manual\_open         | Boolean               | 手动营业开关 |
| open\_time\_morning  | Time                  | 早市开门时间 |
| close\_time\_morning | Time                  | 早市关门时间 |
| open\_time\_evening  | Time                  | 晚市开门时间 |
| close\_time\_evening | Time                  | 晚市关门时间 |
| floor                | Integer               | 所在楼层   |
| image                | ImageField            | 档口图片   |
| canteen\_id          | ForeignKey -> canteen | 所属食堂   |

## 表 5：dish
| 字段名       | 类型                  | 说明                |
|-----------|---------------------|-------------------|
| id        | Integer (PK)        | 主键 ID             |
| name      | Varchar(100)        | 菜品名称              |
| price     | Decimal(6,2)        | 价格                |
| tags      | Varchar(255)        | 标签（可多标签，用 `/` 分隔） |
| image     | ImageField          | 菜品图片              |
| stall\_id | ForeignKey -> stall | 所属档口              |









