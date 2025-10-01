"""Tests for CLI command functions."""

# ruff: noqa: SIM117 - Nested with statements are readable in test context

import argparse
from unittest.mock import patch

import pytest

from eddypro_batch_processor.cli import (
    cmd_run,
    cmd_scenarios,
    cmd_status,
    cmd_validate,
    create_parser,
    main,
    setup_logging,
)


class TestCLICommandFunctions:
    """Test the CLI command handler functions."""

    def test_cmd_run_basic(self):
        """Test the cmd_run function with basic arguments."""
        args = argparse.Namespace(
            config="test_config.yaml",
            site=None,
            years=None,
            dry_run=False,
            rot_meth=None,
            tlag_meth=None,
            detrend_meth=None,
            despike_vm=None,
        )

        with patch("eddypro_batch_processor.cli.logging") as mock_logging:
            result = cmd_run(args)

            assert result == 0
            mock_logging.info.assert_called()
            # Check that proper log messages were called
            call_args = [call[0][0] for call in mock_logging.info.call_args_list]
            assert "Starting EddyPro batch processing run..." in call_args
            assert "Run command - stub implementation" in call_args
            assert f"Config: {args.config}" in call_args

    def test_cmd_run_with_site_override(self):
        """Test cmd_run with site override."""
        args = argparse.Namespace(
            config="test_config.yaml",
            site="TEST-SITE",
            years=None,
            dry_run=False,
            rot_meth=None,
            tlag_meth=None,
            detrend_meth=None,
            despike_vm=None,
        )

        with patch("eddypro_batch_processor.cli.logging") as mock_logging:
            result = cmd_run(args)

            assert result == 0
            call_args = [call[0][0] for call in mock_logging.info.call_args_list]
            assert "Site override: TEST-SITE" in call_args

    def test_cmd_run_with_years_override(self):
        """Test cmd_run with years override."""
        args = argparse.Namespace(
            config="test_config.yaml",
            site=None,
            years=[2021, 2022],
            dry_run=False,
            rot_meth=None,
            tlag_meth=None,
            detrend_meth=None,
            despike_vm=None,
        )

        with patch("eddypro_batch_processor.cli.logging") as mock_logging:
            result = cmd_run(args)

            assert result == 0
            call_args = [call[0][0] for call in mock_logging.info.call_args_list]
            assert "Years override: [2021, 2022]" in call_args

    def test_cmd_run_with_dry_run(self):
        """Test cmd_run with dry run enabled."""
        args = argparse.Namespace(
            config="test_config.yaml",
            site=None,
            years=None,
            dry_run=True,
            rot_meth=None,
            tlag_meth=None,
            detrend_meth=None,
            despike_vm=None,
        )

        with patch("eddypro_batch_processor.cli.logging") as mock_logging:
            result = cmd_run(args)

            assert result == 0
            call_args = [call[0][0] for call in mock_logging.info.call_args_list]
            assert "Dry run mode enabled" in call_args

    def test_cmd_scenarios_basic(self):
        """Test the cmd_scenarios function with basic arguments."""
        args = argparse.Namespace(
            rot_meth=None,
            tlag_meth=None,
            detrend_meth=None,
            despike_vm=None,
            max_scenarios=32,
            site=None,
            years=None,
            config="config/config.yaml",
            metrics_interval=0.5,
        )

        with patch("eddypro_batch_processor.cli.logging") as mock_logging:
            result = cmd_scenarios(args)

            # Should fail with no parameters provided
            assert result == 1
            # Check error was logged
            mock_logging.error.assert_called()

    def test_cmd_scenarios_with_parameters(self):
        """Test cmd_scenarios with various parameters."""
        args = argparse.Namespace(
            rot_meth=[1, 3],
            tlag_meth=[2, 4],
            detrend_meth=[0, 1],
            despike_vm=[0, 1],
            max_scenarios=32,
            site=None,
            years=None,
            config="config/config.yaml",
            metrics_interval=0.5,
        )

        with (
            patch("eddypro_batch_processor.cli.logging") as mock_logging,
            patch(
                "eddypro_batch_processor.cli.core.EddyProBatchProcessor"
            ) as mock_processor_class,
        ):
            # Mock config loading to avoid file system dependencies
            mock_processor = mock_processor_class.return_value
            mock_processor.load_config.return_value = {
                "site_id": "TEST",
                "years_to_process": [2024],
                "eddypro_executable": "test.exe",
                "stream_output": True,
                "input_dir_pattern": "input/{site_id}/{year}",
                "output_dir_pattern": "output/{site_id}/{year}",
                "project_template": "template.ini",
            }
            mock_processor.validate_config.return_value = None

            _result = cmd_scenarios(args)

            # Check that scenario generation was initiated
            assert mock_logging.info.called
            call_args_all = [call[0][0] for call in mock_logging.info.call_args_list]
            # Check for key messages indicating scenario processing
            assert any(
                "Starting scenario matrix processing" in msg for msg in call_args_all
            )
            assert any(
                "Parameter options for scenarios:" in msg for msg in call_args_all
            )

    def test_cmd_validate_basic(self):
        """Test the cmd_validate function with basic arguments."""
        args = argparse.Namespace(
            config="test_config.yaml",
            skip_paths=False,
            skip_ecmd=False,
        )

        with patch("eddypro_batch_processor.cli.logging") as mock_logging:
            result = cmd_validate(args)

            assert result == 0
            call_args = [call[0][0] for call in mock_logging.info.call_args_list]
            assert "Validating configuration and environment..." in call_args
            assert "Validate command - stub implementation" in call_args
            assert f"Config: {args.config}" in call_args

    def test_cmd_validate_with_skip_options(self):
        """Test cmd_validate with skip options."""
        args = argparse.Namespace(
            config="test_config.yaml",
            skip_paths=True,
            skip_ecmd=True,
        )

        with patch("eddypro_batch_processor.cli.logging") as mock_logging:
            result = cmd_validate(args)

            assert result == 0
            call_args = [call[0][0] for call in mock_logging.info.call_args_list]
            assert "Skipping path existence checks" in call_args
            assert "Skipping ECMD file validation" in call_args

    def test_cmd_status_basic(self):
        """Test the cmd_status function with basic arguments."""
        args = argparse.Namespace(
            reports_dir=None,
        )

        with patch("eddypro_batch_processor.cli.logging") as mock_logging:
            result = cmd_status(args)

            assert result == 0
            call_args = [call[0][0] for call in mock_logging.info.call_args_list]
            assert "Checking last run status..." in call_args
            assert "Status command - stub implementation" in call_args

    def test_cmd_status_with_reports_dir(self):
        """Test cmd_status with reports directory override."""
        args = argparse.Namespace(
            reports_dir="/custom/reports/dir",
        )

        with patch("eddypro_batch_processor.cli.logging") as mock_logging:
            result = cmd_status(args)

            assert result == 0
            call_args = [call[0][0] for call in mock_logging.info.call_args_list]
            assert "Reports directory: /custom/reports/dir" in call_args


class TestCLIUtilityFunctions:
    """Test CLI utility functions."""

    def test_setup_logging_default(self):
        """Test setup_logging with default level."""
        with patch("eddypro_batch_processor.cli.logging.basicConfig") as mock_config:
            setup_logging()
            mock_config.assert_called_once()
            # Check that INFO level is used by default
            args, kwargs = mock_config.call_args
            assert kwargs["level"] == 20  # logging.INFO = 20

    def test_setup_logging_debug(self):
        """Test setup_logging with DEBUG level."""
        with patch("eddypro_batch_processor.cli.logging.basicConfig") as mock_config:
            setup_logging("DEBUG")
            mock_config.assert_called_once()
            args, kwargs = mock_config.call_args
            assert kwargs["level"] == 10  # logging.DEBUG = 10

    def test_create_parser(self):
        """Test create_parser function."""
        parser = create_parser()

        assert parser.prog == "eddypro-batch"
        assert "EddyPro Batch Processor" in parser.description

        # Test that it can parse basic arguments
        # Note: we don't actually parse --help because it would sys.exit()
        # Instead test that the parser has the expected subparsers
        assert hasattr(parser, "_subparsers")
        assert parser._subparsers is not None

    def test_create_parser_with_subcommands(self):
        """Test that parser correctly handles subcommands."""
        parser = create_parser()

        # Test run subcommand
        args = parser.parse_args(["run", "--dry-run"])
        assert args.command == "run"
        assert args.dry_run is True

        # Test scenarios subcommand
        args = parser.parse_args(["scenarios", "--rot-meth", "1", "3"])
        assert args.command == "scenarios"
        assert args.rot_meth == [1, 3]

        # Test validate subcommand
        args = parser.parse_args(["validate", "--skip-paths"])
        assert args.command == "validate"
        assert args.skip_paths is True

        # Test status subcommand
        args = parser.parse_args(["status"])
        assert args.command == "status"


class TestMainFunction:
    """Test the main CLI entry point function."""

    def test_main_run_command(self):
        """Test main function routing to run command."""
        test_args = ["eddypro-batch", "run", "--dry-run"]

        with patch("sys.argv", test_args):
            with patch("eddypro_batch_processor.cli.cmd_run") as mock_cmd_run:
                with patch("eddypro_batch_processor.cli.setup_logging"):
                    mock_cmd_run.return_value = 0
                    result = main()

                    assert result == 0
                    mock_cmd_run.assert_called_once()

    def test_main_scenarios_command(self):
        """Test main function routing to scenarios command."""
        test_args = ["eddypro-batch", "scenarios", "--rot-meth", "1"]

        with patch("sys.argv", test_args):
            with patch(
                "eddypro_batch_processor.cli.cmd_scenarios"
            ) as mock_cmd_scenarios:
                with patch("eddypro_batch_processor.cli.setup_logging"):
                    mock_cmd_scenarios.return_value = 0
                    result = main()

                    assert result == 0
                    mock_cmd_scenarios.assert_called_once()

    def test_main_validate_command(self):
        """Test main function routing to validate command."""
        test_args = ["eddypro-batch", "validate"]

        with patch("sys.argv", test_args):
            with patch("eddypro_batch_processor.cli.cmd_validate") as mock_cmd_validate:
                with patch("eddypro_batch_processor.cli.setup_logging"):
                    mock_cmd_validate.return_value = 0
                    result = main()

                    assert result == 0
                    mock_cmd_validate.assert_called_once()

    def test_main_status_command(self):
        """Test main function routing to status command."""
        test_args = ["eddypro-batch", "status"]

        with patch("sys.argv", test_args):
            with patch("eddypro_batch_processor.cli.cmd_status") as mock_cmd_status:
                with patch("eddypro_batch_processor.cli.setup_logging"):
                    mock_cmd_status.return_value = 0
                    result = main()

                    assert result == 0
                    mock_cmd_status.assert_called_once()

    def test_main_no_command_shows_help(self):
        """Test main function with no command shows help."""
        test_args = ["eddypro-batch"]

        with patch("sys.argv", test_args):
            with patch("eddypro_batch_processor.cli.setup_logging"):
                with patch.object(argparse.ArgumentParser, "print_help") as mock_help:
                    result = main()

                    assert result == 1
                    mock_help.assert_called_once()

    def test_main_config_file_not_found(self):
        """Test main function with non-existent config file."""
        test_args = ["eddypro-batch", "--config", "nonexistent.yaml", "validate"]

        with patch("sys.argv", test_args):
            with patch("eddypro_batch_processor.cli.setup_logging"):
                with patch("eddypro_batch_processor.cli.logging") as mock_logging:
                    result = main()

                    assert result == 1
                    mock_logging.error.assert_called()


if __name__ == "__main__":
    pytest.main([__file__])
