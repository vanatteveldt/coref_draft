import sys
import subprocess


def test_main_example(example_naf_file, temp_file, example_naf_output):
    with open(example_naf_file) as fd, open(temp_file, 'w') as out:
        subprocess.check_call(
            [sys.executable, '-m', 'multisieve_coreference'],
            stdin=fd,
            stdout=out
        )
    from KafNafParserPy import KafNafParser
    with open(temp_file) as out, open(example_naf_output) as correct:
        assert KafNafParser(out).coreference_layer is not None
        out.seek(0)
        assert out.read() == correct.read()


def test_main_sonar(sonar_naf_file, temp_file):
    with open(sonar_naf_file) as fd, open(temp_file, 'w') as out:
        subprocess.check_call(
            [sys.executable, '-m', 'multisieve_coreference'],
            stdin=fd,
            stdout=out
        )
    # No gold output available
