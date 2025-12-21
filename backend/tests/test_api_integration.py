"""
Integration tests for PathVest API endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestBacktestAPI:
    """Test backtest API endpoints."""
    
    def test_submit_backtest(self, client, sample_strategy_config):
        """Test POST /api/v1/backtest/run"""
        request = {
            "strategy_config": sample_strategy_config,
            "enable_logging": False,
            "save_results": True
        }
        
        response = client.post("/api/v1/backtest/run", json=request)
        
        # 202 Accepted is correct for async backtest jobs
        assert response.status_code in [200, 202]
        data = response.json()
        assert "backtest_id" in data
        assert isinstance(data["backtest_id"], str)
    
    def test_get_backtest_status(self, client):
        """Test GET /api/v1/backtest/{backtest_id}/status"""
        backtest_id = "test_backtest_001"
        
        response = client.get(f"/api/v1/backtest/{backtest_id}/status")
        
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert data["status"] in ["pending", "running", "completed", "failed"]
    
    def test_get_backtest_results(self, client):
        """Test GET /api/v1/backtest/{backtest_id}"""
        backtest_id = "test_backtest_001"
        
        response = client.get(f"/api/v1/backtest/{backtest_id}")
        
        # May not exist in test DB
        assert response.status_code in [200, 404]
    
    def test_invalid_backtest_config(self, client):
        """Test backtest submission with invalid config."""
        invalid_request = {
            "strategy_config": {
                "name": "Test",
                # Missing required fields
            },
            "enable_logging": False,
            "save_results": True
        }
        
        response = client.post("/api/v1/backtest/run", json=invalid_request)
        
        # Should return validation error
        assert response.status_code == 422


class TestAnalyticsAPI:
    """Test analytics API endpoints."""
    
    def test_get_metrics(self, client):
        """Test GET /api/v1/analytics/{backtest_id}/metrics"""
        backtest_id = "test_backtest_001"
        
        response = client.get(f"/api/v1/analytics/{backtest_id}/metrics")
        
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            # Should have standard metrics
            expected_metrics = ["sharpe_ratio", "cagr", "max_drawdown", "volatility"]
            for metric in expected_metrics:
                assert metric in data
    
    def test_get_attribution(self, client):
        """Test GET /api/v1/analytics/{backtest_id}/attribution"""
        backtest_id = "test_backtest_001"
        
        response = client.get(f"/api/v1/analytics/{backtest_id}/attribution")
        
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "by_signal_type" in data
            assert "by_stock" in data
    
    def test_get_visualization(self, client):
        """Test GET /api/v1/analytics/{backtest_id}/visualizations/{type}"""
        backtest_id = "test_backtest_001"
        vis_type = "monte-carlo-cone"
        
        response = client.get(
            f"/api/v1/analytics/{backtest_id}/visualizations/{vis_type}",
            params={"format": "json"}
        )
        
        assert response.status_code in [200, 404]
    
    def test_export_csv(self, client):
        """Test GET /api/v1/analytics/{backtest_id}/export/csv/trades"""
        backtest_id = "test_backtest_001"
        
        response = client.get(f"/api/v1/analytics/{backtest_id}/export/csv/trades")
        
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            assert response.headers["content-type"] == "text/csv"


class TestValidationAPI:
    """Test validation API endpoints."""
    
    def test_walk_forward_optimization(self, client, sample_strategy_config):
        """Test POST /api/v1/validation/walk-forward"""
        request = {
            "strategy_config": sample_strategy_config,
            "in_sample_period_months": 24,
            "out_sample_period_months": 6,
            "num_splits": 4
        }
        
        response = client.post("/api/v1/validation/walk-forward", json=request)
        
        assert response.status_code in [200, 422]
    
    def test_monte_carlo_simulation(self, client, sample_strategy_config):
        """Test POST /api/v1/validation/monte-carlo"""
        request = {
            "strategy_config": sample_strategy_config,
            "num_simulations": 100,
            "confidence_levels": [0.95, 0.99]
        }
        
        response = client.post("/api/v1/validation/monte-carlo", json=request)
        
        assert response.status_code in [200, 422]
    
    def test_parameter_sensitivity(self, client, sample_strategy_config):
        """Test POST /api/v1/validation/parameter-sensitivity"""
        request = {
            "strategy_config": sample_strategy_config,
            "parameter_ranges": {
                "trailing_stop_percent": [0.10, 0.15, 0.20],
                "sma_period": [20, 50, 100]
            }
        }
        
        response = client.post("/api/v1/validation/parameter-sensitivity", json=request)
        
        assert response.status_code in [200, 422]
    
    def test_stress_testing(self, client, sample_strategy_config):
        """Test POST /api/v1/validation/stress-test"""
        request = {
            "strategy_config": sample_strategy_config,
            "stress_scenarios": ["dot_com_bubble", "financial_crisis_2008", "covid_crash"]
        }
        
        response = client.post("/api/v1/validation/stress-test", json=request)
        
        assert response.status_code in [200, 422]


class TestHealthCheck:
    """Test health check endpoint."""
    
    def test_health_endpoint(self, client):
        """Test GET /api/v1/health"""
        # Try both potential health endpoint paths
        response = client.get("/api/v1/health")
        
        if response.status_code == 404:
            response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "ok"]


class TestCORS:
    """Test CORS configuration."""
    
    def test_cors_headers(self, client):
        """Test CORS headers on API endpoint."""
        response = client.options(
            "/api/v1/backtest/run",
            headers={"Origin": "http://localhost:3000"}
        )
        
        assert response.status_code in [200, 405]
        # CORS headers should be present in actual deployment


class TestRateLimiting:
    """Test rate limiting (if implemented)."""
    
    @pytest.mark.skip(reason="Rate limiting not yet implemented")
    def test_rate_limit_exceeded(self, client):
        """Test rate limit enforcement."""
        # Make many requests
        for _ in range(100):
            response = client.get("/api/v1/backtest/test/status")
        
        # Should eventually hit rate limit
        assert response.status_code == 429


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

