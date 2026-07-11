class ChangeValidator:
    def wait_for_change(self, before_hash: int, timeout: float = 3.0) -> bool:
        raise NotImplementedError("界面变化验证器尚未实现")
