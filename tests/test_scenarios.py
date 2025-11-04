#!/usr/bin/env python3
"""
Unit tests for scenarios module.

Tests scenario generation, Cartesian product, naming, and cap enforcement.
"""

import unittest

from src.eddypro_batch_processor import scenarios


class TestScenarioSuffixGeneration(unittest.TestCase):
    """Test scenario suffix generation."""

    def test_single_parameter_suffix(self):
        """Test suffix with single parameter."""
        params = {"rot_meth": 1}
        suffix = scenarios.generate_scenario_suffix(params)
        self.assertEqual(suffix, "_rot1")

    def test_multiple_parameters_suffix(self):
        """Test suffix with multiple parameters in canonical order."""
        params = {
            "rot_meth": 1,
            "tlag_meth": 2,
            "detrend_meth": 0,
            "despike_meth": 1,
        }
        suffix = scenarios.generate_scenario_suffix(params)
        self.assertEqual(suffix, "_rot1_tlag2_det0_spk1")

    def test_parameters_order_independence(self):
        """Test that parameter order doesn't affect suffix."""
        # Define parameters in different orders
        params1 = {"despike_meth": 0, "rot_meth": 3}
        params2 = {"rot_meth": 3, "despike_meth": 0}

        suffix1 = scenarios.generate_scenario_suffix(params1)
        suffix2 = scenarios.generate_scenario_suffix(params2)

        # Should produce identical suffixes
        self.assertEqual(suffix1, suffix2)
        self.assertEqual(suffix1, "_rot3_spk0")

    def test_empty_parameters(self):
        """Test suffix generation with empty parameters."""
        params: dict[str, int] = {}
        suffix = scenarios.generate_scenario_suffix(params)
        self.assertEqual(suffix, "")

    def test_partial_parameters(self):
        """Test suffix with subset of parameters."""
        params = {"tlag_meth": 4, "detrend_meth": 1}
        suffix = scenarios.generate_scenario_suffix(params)
        self.assertEqual(suffix, "_tlag4_det1")


class TestScenarioGeneration(unittest.TestCase):
    """Test scenario generation with Cartesian product."""

    def test_single_parameter_single_value(self):
        """Test with single parameter and single value."""
        opts = {"rot_meth": [1]}
        scenario_list = scenarios.generate_scenarios(opts)

        self.assertEqual(len(scenario_list), 1)
        self.assertEqual(scenario_list[0].parameters, {"rot_meth": 1})
        self.assertEqual(scenario_list[0].suffix, "_rot1")
        self.assertEqual(scenario_list[0].index, 1)

    def test_single_parameter_multiple_values(self):
        """Test with single parameter and multiple values."""
        opts = {"rot_meth": [1, 3]}
        scenario_list = scenarios.generate_scenarios(opts)

        self.assertEqual(len(scenario_list), 2)

        # Check first scenario
        self.assertEqual(scenario_list[0].parameters, {"rot_meth": 1})
        self.assertEqual(scenario_list[0].suffix, "_rot1")
        self.assertEqual(scenario_list[0].index, 1)

        # Check second scenario
        self.assertEqual(scenario_list[1].parameters, {"rot_meth": 3})
        self.assertEqual(scenario_list[1].suffix, "_rot3")
        self.assertEqual(scenario_list[1].index, 2)

    def test_multiple_parameters_cartesian_product(self):
        """Test Cartesian product with multiple parameters."""
        opts = {"rot_meth": [1, 3], "tlag_meth": [2, 4]}
        scenario_list = scenarios.generate_scenarios(opts)

        # Should produce 2 * 2 = 4 combinations
        self.assertEqual(len(scenario_list), 4)

        # Verify all combinations are present
        expected_combinations = [
            {"rot_meth": 1, "tlag_meth": 2},
            {"rot_meth": 1, "tlag_meth": 4},
            {"rot_meth": 3, "tlag_meth": 2},
            {"rot_meth": 3, "tlag_meth": 4},
        ]

        actual_params = [s.parameters for s in scenario_list]
        for expected in expected_combinations:
            self.assertIn(expected, actual_params)

    def test_three_parameters_cartesian_product(self):
        """Test with three parameters."""
        opts = {"rot_meth": [1, 3], "tlag_meth": [2], "detrend_meth": [0, 1]}
        scenario_list = scenarios.generate_scenarios(opts)

        # Should produce 2 * 1 * 2 = 4 combinations
        self.assertEqual(len(scenario_list), 4)

        # Check that indices are sequential
        indices = [s.index for s in scenario_list]
        self.assertEqual(indices, [1, 2, 3, 4])

    def test_deterministic_ordering(self):
        """Test that scenario generation is deterministic."""
        opts = {"rot_meth": [1, 3], "despike_meth": [0, 1]}

        # Generate scenarios multiple times
        scenarios1 = scenarios.generate_scenarios(opts)
        scenarios2 = scenarios.generate_scenarios(opts)

        # Should produce identical results
        self.assertEqual(len(scenarios1), len(scenarios2))
        for s1, s2 in zip(scenarios1, scenarios2, strict=False):
            self.assertEqual(s1.parameters, s2.parameters)
            self.assertEqual(s1.suffix, s2.suffix)
            self.assertEqual(s1.index, s2.index)


class TestScenarioCapEnforcement(unittest.TestCase):
    """Test scenario cap enforcement."""

    def test_exactly_at_cap(self):
        """Test scenario generation exactly at the cap."""
        # Generate exactly 32 scenarios (4 * 4 * 2 = 32)
        opts = {
            "rot_meth": [1, 3],
            "tlag_meth": [2, 4],
            "detrend_meth": [0, 1],
            "despike_meth": [0, 1, 2, 3],  # Hypothetical extra values
        }

        # Should succeed (or adjust to actual valid values)
        # For now, testing with valid values: 2 * 2 * 2 * 2 = 16
        opts = {
            "rot_meth": [1, 3],
            "tlag_meth": [2, 4],
            "detrend_meth": [0, 1],
            "despike_meth": [0, 1],
        }
        scenario_list = scenarios.generate_scenarios(opts, max_scenarios=16)
        self.assertEqual(len(scenario_list), 16)

    def test_exceeds_cap(self):
        """Test that exceeding cap raises error."""
        # Try to generate 2^6 = 64 scenarios (exceeds default cap of 32)
        opts = {
            "rot_meth": [1, 3],
            "tlag_meth": [2, 4],
            "detrend_meth": [0, 1],
            "despike_meth": [0, 1],
        }

        # Set a low cap to test enforcement
        with self.assertRaises(scenarios.ScenarioLimitExceededError) as context:
            scenarios.generate_scenarios(opts, max_scenarios=2)

        error_msg = str(context.exception)
        self.assertIn("exceeds maximum", error_msg.lower())
        self.assertIn("16", error_msg)  # Actual count
        self.assertIn("2", error_msg)  # Max allowed

    def test_custom_max_scenarios(self):
        """Test with custom max_scenarios parameter."""
        opts = {"rot_meth": [1, 3], "tlag_meth": [2, 4]}

        # Should succeed with max 10
        scenario_list = scenarios.generate_scenarios(opts, max_scenarios=10)
        self.assertEqual(len(scenario_list), 4)

        # Should fail with max 2
        with self.assertRaises(scenarios.ScenarioLimitExceededError):
            scenarios.generate_scenarios(opts, max_scenarios=2)


class TestScenarioValidation(unittest.TestCase):
    """Test scenario validation."""

    def test_empty_parameter_options_error(self):
        """Test that empty parameter options raises error."""
        opts: dict[str, list[int]] = {}

        with self.assertRaises(ValueError) as context:
            scenarios.generate_scenarios(opts)

        self.assertIn("empty", str(context.exception).lower())

    def test_empty_value_list_error(self):
        """Test that empty value list raises error."""
        opts = {"rot_meth": [], "tlag_meth": [2]}

        with self.assertRaises(ValueError) as context:
            scenarios.generate_scenarios(opts)

        error_msg = str(context.exception)
        self.assertIn("rot_meth", error_msg)
        self.assertIn("no values", error_msg.lower())

    def test_validate_scenario_parameters(self):
        """Test parameter option validation."""
        opts = {"rot_meth": [1, 3], "tlag_meth": [2, 4]}

        # Should succeed
        validated = scenarios.validate_scenario_parameters(opts)
        self.assertEqual(validated, opts)

    def test_validate_unrecognized_parameter(self):
        """Test validation with unrecognized parameter."""
        opts = {"invalid_param": [1, 2]}

        with self.assertRaises(ValueError) as context:
            scenarios.validate_scenario_parameters(opts)

        error_msg = str(context.exception)
        self.assertIn("unrecognized", error_msg.lower())
        self.assertIn("invalid_param", error_msg)


class TestScenarioDataclass(unittest.TestCase):
    """Test Scenario dataclass behavior."""

    def test_scenario_creation(self):
        """Test creating a Scenario object."""
        params = {"rot_meth": 1, "tlag_meth": 2}
        suffix = "_rot1_tlag2"
        index = 1

        scenario = scenarios.Scenario(
            parameters=params,
            suffix=suffix,
            index=index,
        )

        self.assertEqual(scenario.parameters, params)
        self.assertEqual(scenario.suffix, suffix)
        self.assertEqual(scenario.index, index)

    def test_scenario_immutable(self):
        """Test that Scenario is immutable (frozen)."""
        scenario = scenarios.Scenario(
            parameters={"rot_meth": 1},
            suffix="_rot1",
            index=1,
        )

        # Should not be able to modify
        with self.assertRaises(AttributeError):
            scenario.index = 2  # type: ignore[misc]

    def test_scenario_invalid_empty_parameters(self):
        """Test that empty parameters raises error."""
        with self.assertRaises(ValueError):
            scenarios.Scenario(
                parameters={},
                suffix="",
                index=1,
            )

    def test_scenario_invalid_empty_suffix(self):
        """Test that empty suffix raises error."""
        with self.assertRaises(ValueError):
            scenarios.Scenario(
                parameters={"rot_meth": 1},
                suffix="",
                index=1,
            )

    def test_scenario_invalid_zero_index(self):
        """Test that zero index raises error."""
        with self.assertRaises(ValueError):
            scenarios.Scenario(
                parameters={"rot_meth": 1},
                suffix="_rot1",
                index=0,
            )


class TestScenarioSummaryFormatting(unittest.TestCase):
    """Test scenario summary formatting."""

    def test_format_empty_scenarios(self):
        """Test formatting empty scenario list."""
        scenario_list: list[scenarios.Scenario] = []
        summary = scenarios.format_scenario_summary(scenario_list)

        self.assertIn("no scenarios", summary.lower())

    def test_format_single_scenario(self):
        """Test formatting single scenario."""
        scenario_list = scenarios.generate_scenarios({"rot_meth": [1]})
        summary = scenarios.format_scenario_summary(scenario_list)

        self.assertIn("1 scenario", summary.lower())
        self.assertIn("Scenario 1", summary)
        self.assertIn("rot_meth=1", summary)
        self.assertIn("_rot1", summary)

    def test_format_multiple_scenarios(self):
        """Test formatting multiple scenarios."""
        scenario_list = scenarios.generate_scenarios(
            {"rot_meth": [1, 3], "tlag_meth": [2]}
        )
        summary = scenarios.format_scenario_summary(scenario_list)

        self.assertIn("2 scenario", summary.lower())
        self.assertIn("Scenario 1", summary)
        self.assertIn("Scenario 2", summary)


if __name__ == "__main__":
    unittest.main()
