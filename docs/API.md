# API接口参考
## 1. 欢迎页（welcome）

| 接口名称              | 请求方法 | URL 路径                 | 请求参数                            | 返回数据格式                                                                                                          | 说明           |
|-------------------|------|------------------------|---------------------------------|-----------------------------------------------------------------------------------------------------------------|--------------|
| **获取欢迎页数据**       | GET  | `/unieat/api/welcome/` | 无                               | `json\n{\n  "id": 1,\n  "title": "欢迎来到 Unieat",\n  "image_url": "http://127.0.0.1:8000/media/welcome.jpg"\n}\n` | 返回欢迎页图片与标题   |
| **上传欢迎页数据（后台管理）** | POST | `/unieat/api/welcome/` | `title` (string)，`image` (file) | 成功或错误信息 JSON                                                                                                    | 管理员上传新的欢迎页信息 |

## 2. 首页（home）
| 接口名称      | 请求方法 | URL 路径                  | 请求参数 | 返回数据格式                                                                                                                                                                                  | 说明                           |
|-----------|------|-------------------------|------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------|
| **获取问候语** | GET  | `/unieat/api/greeting/` | 无    | `json\n{\n  "greeting": "早上好！Claire"\n}\n`                                                                                                                                              | 返回当前问候语（根据时间变化）              |
| **获取轮播图** | GET  | `/unieat/api/banners/`  | 无    | `json\n[\n  {\n    "id": 1,\n    "image_url": "http://127.0.0.1:8000/media/banner1.jpg"\n  },\n  {\n    "id": 2,\n    "image_url": "http://127.0.0.1:8000/media/banner2.jpg"\n  }\n]\n` | 返回最新的 3 条轮播图数据（按 `order` 倒序） |

## 3. 菜品-档口-食堂
| 接口路径                      | 方法  | 描述             | 参数                                                                    | 返回示例（精简版）                                                   |
|---------------------------|-----|----------------|-----------------------------------------------------------------------|-------------------------------------------------------------|
| `/api/canteens/`          | GET | 获取所有食堂列表       | 无                                                                     | `[{id, name, location, opening_hours, stall_count, image}]` |
| `/api/canteens/{id}/`     | GET | 获取单个食堂详情       | `id`（路径参数）                                                            | `{id, name, location, stalls: [...]}`                       |
| `/api/canteens/full_data` | GET | 获取食堂-档口-菜品完整数据 | `id`（可选，指定食堂）<br>`only_open`（true/false，可选）<br>`random_dishes`（整数，可选） | `{status: "success", count: N, data: [...]}`                |
| `/api/stalls/`            | GET | 获取所有档口列表       | 无                                                                     | `[{id, name, cuisine_type, image, dishes: [...] }]`         |
| `/api/stalls/{id}/`       | GET | 获取单个档口详情       | `id`（路径参数）                                                            | `{id, name, cuisine_type, dishes: [...]}`                   |
| `/api/dishes/`            | GET | 获取所有菜品列表       | 无                                                                     | `[{id, name, price, tags, image, stall}]`                   |
| `/api/dishes/{id}/`       | GET | 获取单个菜品详情       | `id`（路径参数）                                                            | `{id, name, price, tags, stall: {...}}`                     |
### 3\* 详情显示
| API 名称                   | 请求方式 | 路径                          | 返回内容简要说明                                                |
|--------------------------|------|-----------------------------|---------------------------------------------------------|
| **DishDetailAPIView**    | GET  | `/unieat/api/dish/{id}/`    | 返回单个菜品的完整信息，包含：菜品名、价格、图片、所属档口、所属食堂等。                    |
| **StallDetailAPIView**   | GET  | `/unieat/api/stall/{id}/`   | 返回单个档口详情，包含：档口名、楼层、所属食堂、档口图片、所有菜品（简化信息：id/名称/价格/图片）、均价。 |
| **CanteenDetailAPIView** | GET  | `/unieat/api/canteen/{id}/` | 返回单个食堂详情，包含：食堂名、图片、所有档口（id/名称/楼层/图片），可在前端按楼层筛选显示。       |

## 4.用户信息
| API                  | 方法   | 请求数据                                                     | 返回数据                     | 说明                |
|----------------------|------|----------------------------------------------------------|--------------------------|-------------------|
| `/api/user/login/`   | POST | `{code: "wx.login() 返回的 code"}`                          | `{access, refresh}`      | 登录，返回 JWT         |
| `/api/user/me/`      | GET  | Header: `Authorization: Bearer <access>`                 | `{id, username, openid}` | 校验 token 是否有效     |
| `/api/user/profile/` | GET  | Header: `Authorization`                                  | `{nickname, avatar_url}` | 获取当前用户资料          |
| `/api/user/profile/` | POST | Header: `Authorization` + Body: `{nickname, avatar_url}` | `{nickname, avatar_url}` | 更新用户资料（仅传需要修改的字段） |
