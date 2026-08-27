import unittest
from unittest.mock import patch, MagicMock
from TAC_to_csv import TacConversionToolApp
import os

class TestTacConversionToolApp(unittest.TestCase):

    @patch('TAC_to_csv.filedialog.askopenfilename')
    def test_open_tac_file_dialog_sets_file_path(self, mock_askopenfilename):
        mock_askopenfilename.return_value = "C:/path/to/test.TAC.zip"
        app = TacConversionToolApp()
        app.open_tac_file_dialog()
        self.assertEqual(app.tac_file_path.get(), "C:/path/to/test.TAC.zip")

    @patch('TAC_to_csv.filedialog.askopenfilename')
    def test_open_adb_file_dialog_sets_file_path(self, mock_askopenfilename):
        mock_askopenfilename.return_value = "C:/path/to/test.ADB.zip"
        app = TacConversionToolApp()
        app.open_adb_file_dialog()
        self.assertEqual(app.adb_file_path.get(), "C:/path/to/test.ADB.zip")

    @patch('TAC_to_csv.filedialog.askdirectory')
    @patch('os.path.exists')
    @patch('os.mkdir')
    def test_select_output_folder_creates_new_folder(self, mock_mkdir, mock_exists, mock_askdirectory):
        mock_askdirectory.return_value = "C:/path/to/output"
        mock_exists.return_value = False
        app = TacConversionToolApp()
        app.select_output_folder()
        mock_mkdir.assert_called_once_with("C:/path/to/output/output")
        self.assertEqual(app.output_file_name.get(), "C:/path/to/output/output")

    @patch('TAC_to_csv.filedialog.askdirectory')
    @patch('os.path.exists')
    @patch('os.mkdir')
    def test_select_output_folder_uses_existing_folder(self, mock_mkdir, mock_exists, mock_askdirectory):
        mock_askdirectory.return_value = "C:/path/to/output"
        mock_exists.return_value = True
        app = TacConversionToolApp()
        app.select_output_folder()
        mock_mkdir.assert_not_called()
        self.assertEqual(app.output_file_name.get(), "C:/path/to/output/output")

    @patch('os.path.exists')
    @patch('os.makedirs')
    @patch('TAC_to_csv.generate_injection_plots_from_injection_csv')
    def test_on_convert_tac_generates_plots(self, mock_generate_plots, mock_makedirs, mock_exists):
        mock_exists.side_effect = lambda path: path.endswith("injection.csv") or path.endswith("output")
        app = TacConversionToolApp()
        app.tac_file_path.set("C:/path/to/test.TAC.zip")
        app.adb_file_path.set("C:/path/to/test.ADB.zip")
        app.output_file_name.set("C:/path/to/output")
        app.generate_plots_var.set(True)
        app.on_convert_tac()
        mock_generate_plots.assert_called_once()

    @patch('os.path.exists')
    @patch('TAC_to_csv.process_mcu_log_or_zip')
    @patch('TAC_to_csv.process_adb_or_tac_files')
    def test_on_convert_tac_processes_files(self, mock_process_adb_or_tac, mock_process_mcu_log, mock_exists):
        mock_exists.return_value = True
        app = TacConversionToolApp()
        app.tac_file_path.set("C:/path/to/test.TAC.zip")
        app.adb_file_path.set("C:/path/to/test.ADB.zip")
        app.output_file_name.set("C:/path/to/output")
        app.on_convert_tac()
        mock_process_mcu_log.assert_called_once_with("C:/path/to/test.TAC.zip", "C:/path/to/output", new_oad=True)
        mock_process_adb_or_tac.assert_called_once_with("C:/path/to/test.ADB.zip", "C:/path/to/test.TAC.zip", "C:/path/to/output", False)

if __name__ == '__main__':
    unittest.main()
