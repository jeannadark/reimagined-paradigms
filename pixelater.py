import os
import threading as th
import numpy as np
import matplotlib.pylab as plt
import sys
import cv2
import time


class Runner:
    """Consolidates chunking, threading and pixelating in one class."""

    def __init__(self, file_name, square_size, process_mode):
        """Perform initialization.

        :param file_name: name of the input image
        :param square_size: size of the box
        :param process_mode: single- or multi-threaded
        """
        self.file_name = file_name
        self.square_size = square_size
        self.processing_mode = process_mode
        self.boxes = []
        self.pixelated_image = np.zeros((0, 0, 0), dtype=int)

    def chunker(self):
        """Adjust the image dimensions so that the squares fit the picture.

        Further, break the image dimensions down into chunks of equal size.
        Store the chunks in an array (class variable).
        """
        input_image = plt.imread(self.file_name)

        h = input_image.shape[0] - input_image.shape[0] % self.square_size
        w = input_image.shape[1] - input_image.shape[1] % self.square_size

        self.pixelated_image = input_image[0:h, 0:w].copy()

        # break the image down into square chunks

        for x in range(0, h, self.square_size):
            dim_1 = (x, x + self.square_size)
            for y in range(0, w, self.square_size):
                dim_2 = (y, y + self.square_size)
                self.boxes.append((dim_1, dim_2))

    def single_pixelizer(self, n_jobs, input_image):
        """Process a given number of image chunks in a single thread.

        Assign the average of each color channel for each chunk.
        Display the output image as the processing progresses.
        This function will change the pixelated image in place.

        :param n_jobs: number of chunks to process per thread
        :param input_image: non-adjusted input image
        """
        for i in range(n_jobs):

            (x0, x1), (y0, y1) = self.boxes.pop(0)

            self.pixelated_image[x0:x1, y0:y1, 0] = input_image[x0:x1, y0:y1, 0].mean()
            self.pixelated_image[x0:x1, y0:y1, 1] = input_image[x0:x1, y0:y1, 1].mean()
            self.pixelated_image[x0:x1, y0:y1, 2] = input_image[x0:x1, y0:y1, 2].mean()

            # resize the image to an arbitrary size for easier display
            image = cv2.resize(self.pixelated_image, (500, 500))
            # ensure RGB colors are displayed
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

            cv2.imshow("Result", image)
            cv2.waitKey(30)

    def multi_pixelizer(self, n_jobs, input_image, lock):
        """Process a given number of image chunks in multiple threads.

        Assign the average of each color channel for each chunk.
        This function will change the pixelated image in place.

        :param n_jobs: number of chunks to process per thread
        :param input_image: non-adjusted input image
        :param lock: lock to be acquired by threads to prevent unwanted clashes
        """
        for i in range(n_jobs):

            lock.acquire()

            (x0, x1), (y0, y1) = self.boxes.pop(0)

            self.pixelated_image[x0:x1, y0:y1, 0] = input_image[x0:x1, y0:y1, 0].mean()
            self.pixelated_image[x0:x1, y0:y1, 1] = input_image[x0:x1, y0:y1, 1].mean()
            self.pixelated_image[x0:x1, y0:y1, 2] = input_image[x0:x1, y0:y1, 2].mean()

            lock.release()

    def processor(self, input_image):
        """Process the image in either single- or multi-threaded mode.

        Create number of threads equal to CPU cores in case of multithreading.
        Divide the chunks equally among threads.
        Display the output image as the processing progresses.

        In case of single-threaded mode, process all chunks in the main thread.
        Return the final fully processed image.

        :param input_image: non-adjusted input image
        :return: processed image
        """
        if self.processing_mode == "M":

            n_threads = os.cpu_count()
            n_jobs_per_thread = len(self.boxes) // n_threads

            # there might be some leftover jobs that could not get divided, so assign them to the last thread
            leftover_jobs = len(self.boxes) - n_jobs_per_thread * n_threads
            n_jobs_for_last_thread = n_jobs_per_thread + leftover_jobs

            lock = th.Lock()

            # create a thread pool and the last thread separately, so that the latter can take leftover jobs as well
            threads = [
                th.Thread(
                    target=self.multi_pixelizer, args=(n_jobs_per_thread, input_image, lock)
                )
                for t in range(n_threads - 1)
            ]
            last_thread = th.Thread(
                target=self.multi_pixelizer, args=(n_jobs_for_last_thread, input_image, lock)
            )

            [t.start() for t in threads]
            last_thread.start()

            # keep displaying the image until execution finishes
            while len(self.boxes) > 0:

                image = cv2.resize(self.pixelated_image, (500, 500))
                image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

                cv2.imshow("Result", image)
                cv2.waitKey(50)

            [t.join() for t in threads]
            last_thread.join()

        elif self.processing_mode == "S":

            n_jobs_per_thread = len(self.boxes)
            self.single_pixelizer(n_jobs_per_thread, input_image)

        return self.pixelated_image


def main():

    file_name = str(sys.argv[1])
    square_size = int(sys.argv[2])
    processing_mode = str(sys.argv[3])

    input_image = plt.imread(file_name)

    start = time.time()

    image_processor = Runner(file_name, square_size, processing_mode)
    image_processor.chunker()
    result_image = image_processor.processor(input_image)
    stop = time.time()

    cv2.destroyAllWindows()

    plt.imsave("result.jpg", result_image)
    print("Saved the result in the current working directory.")
    print("Elapsed time: ", stop - start, " seconds.")


if __name__ == "__main__":

    main()
