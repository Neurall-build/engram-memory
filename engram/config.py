# SPDX-License-Identifier: BUSL-1.1
# Copyright (c) 2026 Neurall. All rights reserved.
# Licensed under the Business Source License 1.1
# See LICENSE file in the root of this repository.

"""Pydantic settings for ENGRAM configuration.

Reads all ENGRAM_ prefixed environment variables from .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """ENGRAM application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_prefix="ENGRAM_", env_file=".env", extra="ignore")

    db_path: str = Field(default="./engram.db", alias="ENGRAM_DB_PATH")
    env: str = Field(default="development", alias="ENGRAM_ENV")
    embed_dim: int = Field(default=1536, alias="ENGRAM_EMBED_DIM")
    decay_lambda: float = Field(default=0.0001, alias="ENGRAM_DECAY_LAMBDA")
    decay_threshold: float = Field(default=0.05, alias="ENGRAM_DECAY_THRESHOLD")
    api_prefix: str = Field(default="/v1", alias="ENGRAM_API_PREFIX")
    host: str = Field(default="127.0.0.1", alias="ENGRAM_HOST")
    port: int = Field(default=8000, alias="ENGRAM_PORT")
    hive_enabled: bool = Field(default=False, alias="ENGRAM_HIVE_ENABLED")
    hive_org_id: str = Field(default="", alias="ENGRAM_HIVE_ORG_ID")


settings = Settings()
