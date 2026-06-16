---
title: Unity 中 ScrollRect 多指滑动的冲突解决方案
published: 2026-06-16
description: 记录 SuperScrollView 的 LoopListView2 在双指滑动时闪烁的问题定位，以及通过 Input.multiTouchEnabled 在公共脚本中统一屏蔽多指输入的处理方案。
tags: [游戏开发, Unity, ScrollRect, SuperScrollView, UGUI]
category: 游戏开发
draft: false
---

## 需求背景

用 SuperScrollView 的 `LoopListView2` 做了一个可滑动的列表，玩家拖动浏览。测试提了个缺陷：双指同时在列表上滑动时，列表会在两指之间来回跳，画面闪烁。

期望的行为是：一根手指在滑动时，后续落下的其它手指都该被屏蔽，不管是接着滑还是点 item。

还有个硬约束：**不能改 prefab**。列表被几十个界面复用，逐个改组件成本和回归风险都太高。所以方案只能动公共代码，一处生效。

---

## 谁在驱动滚动

动手前要先搞清楚一件事：真正让列表滚动的是谁。`LoopListView2` 初始化时从同一个 GameObject 上拿了 Unity 自带的 `ScrollRect`：

```csharp
mScrollRect = gameObject.GetComponent<ScrollRect>();
```

也就是说这个物体上挂了两个都实现 `IDragHandler` 的组件：`ScrollRect`（它才真正移动 content）和 `LoopListView2`（只做 snap 之类的辅助逻辑）。EventSystem 派发拖拽事件时，会分别发给物体上每一个实现了接口的组件。

所以一个很自然但没用的写法，是在 `LoopListView2` 里用 `pointerId` 把第二根手指挡掉：

```csharp
public virtual void OnBeginDrag(PointerEventData eventData) {
    if (mIsDraging) {
        return;          // 只让 LoopListView2 自己提前返回
    }
    mDragPointerId = eventData.pointerId;
    mIsDraging = true;
}
```

这只能管住 `LoopListView2` 一个组件，第二根手指的事件照样发给隔壁的 `ScrollRect`，而 `ScrollRect` 不看 `pointerId`，照滚不误。拦的位置错了。

社区成熟方案 `MultiTouchScrollRect` 是继承 `ScrollRect` 重写拖拽，但要替换每个 prefab 上的组件，撞约束，排除。

---

## 解决方案

### 1. 拦在输入层

应用层拦不住 `ScrollRect`，那就上移到最上游的输入层。手指事件的链路是：

```text
Input（底层采集 touch）→ EventSystem 分发 → 各组件（ScrollRect / LoopListView2）
```

只要在 Input 层就把多余的手指掐掉，下游所有组件都收不到第二根手指，自然全部失效。旧版 Input Manager 正好有这个开关：

```csharp
Input.multiTouchEnabled = false;   // 关闭后只上报第一根手指
```

> 这招的前提是项目用旧版 Input Manager（`ProjectSettings` 里 `activeInputHandler: 0`），新版 Input System 下这个开关无效。

### 2. 别整程关，会吞掉下一次滑动

最直觉的写法是第一根手指按下就关、抬起就恢复。闪烁确实没了，但又冒出个新问题：单指快速连滑（滑→松→马上再滑）时，第二次会被吞掉。

原因是 `multiTouchEnabled = false` 期间落下的手指拿不到 `TouchPhase.Began`。快速连滑时后一根手指常在前一根还没抬起、开关还关着的那几毫秒就落下了，它拿不到 `Began`，EventSystem 就不会派 `OnBeginDrag`，这次滑动整段失效。

所以要把“关”的时机收窄到真正出现第二根手指的那一刻。

### 3. 按需关 + 重新锚定

字段：

```csharp
bool mIsDraging = false;
int mDragPointerId = -1;
bool mMultiTouchBlocked = false;    // 是否已临时关闭多点触控
bool mNeedReanchorScroll = false;   // 下一次 OnDrag 是否需要重新锚定 ScrollRect
```

`OnBeginDrag` 里，只有当已经在拖拽、又来了第二根手指时才关：

```csharp
public virtual void OnBeginDrag(PointerEventData eventData) {
    if (eventData.button != PointerEventData.InputButton.Left) {
        return;
    }
    if (mIsDraging) {
        // 拖拽中又落下第二根手指，此刻才关多点触控屏蔽它。
        // 不在第一根手指按下时就关，否则单指快速连滑的下一次会被吞。
        if (!mMultiTouchBlocked) {
            Input.multiTouchEnabled = false;
            mMultiTouchBlocked = true;
            mNeedReanchorScroll = true;
        }
        return;
    }
    mDragPointerId = eventData.pointerId;
    mIsDraging = true;
    CacheDragPointerEventData(eventData);
}
```

第二根手指的 `OnBeginDrag` 会顺带改写 `ScrollRect` 的拖拽基准，不处理的话第一根手指下一帧会算出一个大位移，跳一下。所以在下一次有效手指的 `OnDrag` 里，用它当前位置重新锚定一次：

```csharp
public virtual void OnDrag(PointerEventData eventData) {
    if (eventData.button != PointerEventData.InputButton.Left) {
        return;
    }
    if (eventData.pointerId != mDragPointerId) {
        return;
    }
    CacheDragPointerEventData(eventData);
    if (mNeedReanchorScroll) {
        // 第二根手指改写了 ScrollRect 的基准，用有效手指重新锚定，避免跳变。
        mNeedReanchorScroll = false;
        mScrollRect.OnBeginDrag(eventData);
    }
    if (mOnDragingAction != null) {
        mOnDragingAction();
    }
}
```

关掉的多点触控要成对恢复，否则会把全局多点触控永久关掉。除了正常结束的 `OnEndDrag`，`OnDisable` 也要兜底：拖到一半界面被关时同样要恢复。

```csharp
public virtual void OnEndDrag(PointerEventData eventData) {
    if (eventData.button != PointerEventData.InputButton.Left) {
        return;
    }
    if (eventData.pointerId != mDragPointerId) {
        return;
    }
    mDragPointerId = -1;
    mIsDraging = false;
    RestoreMultiTouch();
}

void RestoreMultiTouch() {
    mNeedReanchorScroll = false;
    if (mMultiTouchBlocked) {
        mMultiTouchBlocked = false;
        Input.multiTouchEnabled = true;
    }
}

void OnDisable() {
    mIsDraging = false;
    mDragPointerId = -1;
    RestoreMultiTouch();
}
```

> 真・两指重叠（一指没抬起、另一指已落下）仍可能丢一次输入，这是输入层屏蔽的固有代价，但属于异常操作，比持续闪烁好得多，可接受。

---

## 总结

| 问题 | 解决方案 |
|------|----------|
| 双指滑动闪烁 | 拦截点从应用层上移到输入层 `Input.multiTouchEnabled` |
| 单指快速连滑被吞 | 不整程关，只在检测到第二根手指时才关 |
| 第二指污染基准导致跳变 | 下一次 `OnDrag` 用有效手指重新锚定 |
| 开关泄漏 | `OnEndDrag` + `OnDisable` 成对恢复 |

改动全在 `LoopListView2` 一个公共脚本里，不碰任何 prefab，对所有列表一处生效。
