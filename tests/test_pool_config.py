def test_pool_defaults_raised():
    from sage_poc import config
    assert config.DB_POOL_MAX_SIZE >= 20
    assert config.HTTP_MAX_KEEPALIVE >= 20
    assert config.HTTP_MAX_CONNECTIONS >= 100


def test_llm_http_limits_use_config():
    from sage_poc import llm, config
    limits = llm._http_limits()
    assert limits.max_keepalive_connections == config.HTTP_MAX_KEEPALIVE
    assert limits.max_connections == config.HTTP_MAX_CONNECTIONS
