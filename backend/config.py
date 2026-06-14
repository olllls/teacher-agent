from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "TeacherEval Agent"
    debug: bool = False

    database_url: str = "sqlite+aiosqlite:///./data/teacher_eval.db"

    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"

    upload_dir: str = "uploads"
    export_dir: str = "exports"
    max_upload_size: int = 10 * 1024 * 1024  # 10MB

    default_words_per_eval: str = "100-150"
    default_style: str = "encourage"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
