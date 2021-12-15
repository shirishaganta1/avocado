import enum
import os
from mmap import ACCESS_READ, mmap
from pathlib import Path

from avocado.core.data_dir import get_job_results_dir
from avocado.core.settings import settings
from avocado.core.spawners.exceptions import SpawnerException
from avocado.utils.astring import string_to_safe_path


class SpawnMethod(enum.Enum):
    """The method employed to spawn a runnable or task."""
    #: Spawns by running executing Python code, that is, having access to
    #: a runnable or task instance, it calls its run() method.
    PYTHON_CLASS = object()
    #: Spawns by running a command, that is having either a path to an
    #: executable or a list of arguments, it calls a function that will
    #: execute that command (such as with os.system())
    STANDALONE_EXECUTABLE = object()
    #: Spawns with any method available, that is, it doesn't declare or
    #: require a specific spawn method
    ANY = object()


class SpawnerMixin:
    """Common utilities for Spawner implementations."""

    METHODS = []

    def __init__(self, config=None):
        if config is None:
            config = settings.as_dict()
        self.config = config
        self.job_output_dir = None

    def task_output_dir(self, runtime_task):
        return os.path.join(self.job_output_dir,
                            runtime_task.task.identifier.str_filesystem)

    @staticmethod
    def bytes_from_file(filename):
        """Read bytes from a files in binary mode.

        This is a helpful method to read *local* files bytes efficiently.

        If the spawner that you are implementing needs access to local file,
        feel free to use this method.
        """
        # This could be optimized in the future.
        with open(filename, 'rb', 0) as fp:
            with mmap(fp.fileno(), 0, access=ACCESS_READ) as stream:
                yield stream.read()

    @staticmethod
    def stream_output(job_id, task_id):
        """Returns output files streams in binary mode from a task.

        This method will find for output files generated by a task and will
        return a generator with tuples, each one containing a filename and
        bytes.

        You need to provide in your spawner a `stream_output()` method if this
        one is not suitable for your spawner. i.e: if the spawner is trying to
        access a remote output file.
        """
        results_dir = get_job_results_dir(job_id)
        task_id = string_to_safe_path(task_id)
        data_pointer = '{}/test-results/{}/data'.format(results_dir, task_id)
        src = open(data_pointer, 'r').readline().rstrip()
        try:
            for path in Path(src).expanduser().iterdir():
                if path.is_file() and path.stat().st_size != 0:
                    for stream in SpawnerMixin.bytes_from_file(str(path)):
                        yield (path.name, stream)
        except FileNotFoundError as e:
            raise SpawnerException("Task not found: {}".format(e))
