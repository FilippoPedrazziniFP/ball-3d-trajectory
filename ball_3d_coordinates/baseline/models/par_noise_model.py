from __future__ import absolute_import

import numpy as np
from numpy.linalg import pinv

class ParabolaNoiseModel(object):
    """ The model is described in the paper: 
        Estimating 3D Positions and Velocities of Projectiles from Monocular Views. 
        The objective of this method is to deal with the noise generated by a real
        dataset. The intuition behind the method regards the fact that each frame has the 
        same weigth instead of having a weight base on the temporal information.

        """
    def __init__(self):
        super(ParabolaNoiseModel, self).__init__()
        self.calibration = CameraCalibrationBuilder.build(cam_cal_method)
        self.proj_matrix = self.calibration.compute_camera_calibration()
        self.g = -9.8
        self.lr = 0.1
        self.parameters = self.initialize_parameters()

    def initialize_parameters(self):
        """ The method initializes the 6 parameters needed 
            for the training task. """
        return np.random.uniform(0.5, 1, 6)

    def loss_function(self, time, P1, P2, P3, Xt, Yt, parameters):
        """ The method computes the loss function with 
            the six parameters as described in the paper """
        Qt = np.array((parameters[0] - parameters[1]*time, 
                        parameters[2] - parameters[3]*time + 0.5 * self.g * (time**2),
                        parameters[4] - parameters[5]*time,
                        1))

        Xt_pred = np.dot(P1, Qt)/np.dot(P3, Qt)
        Yt_pred = np.dot(P2, Qt)/np.dot(P3, Qt)

        err = (Xt - Xt_pred)**2 + (Yt - Yt_pred)**2
        return err

    def derivative(self, loss_function, time, P1, P2, P3, Xt, Yt, parameters, delta=10e-8):
        """ The method computes the derivative of the loss function with 
            respect to the passed parameters. """
        params = []
        for i in range(0, len(parameters)):
            tmp = np.zeros((len(parameters)))
            tmp[i] = delta
            result = (loss_function(time, P1, P2, P3, Xt, Yt, parameters + tmp) - loss_function(time, P1, P2, P3, Xt, Yt, parameters - tmp)) / (2*delta)
            params.append(result)
        return np.asarray(params)


    def train(self, features, time, epochs=10):
        """ Having the projection matrix (C), the parabola model equations (E) and the object 
            position in the 2D image at time zero (feature), we can estimate the 
            missing values (X0, Vx0, Y0, Vy0, Z0, Vz0) using a minimization approach. 

            X0 = min || (Xt, Yt) - (X^t, Y^t) ||22

            """
        T = time/25
        C = self.get_projection_matrix()

        P1 = C[0,:]
        P2 = C[1,:]
        P3 = C[2,:]

        for i, feature in enumerate(features):
            derivatives = self.derivative(self.loss_function, 
                T, P1, P2, P3, feature[0], 
                feature[1], self.parameters)
            T = T + 1/25
            self.parameters -= self.lr * derivatives
        
        self.initial_x = self.parameters[0]
        self.v_x = self.parameters[1]
        self.initial_y = self.parameters[2]
        self.v_y = self.parameters[3]
        self.initial_z = self.parameters[4]
        self.v_z = self.parameters[5]

        return

    def inference(self, t):
        """ The method returns the prediction using the
            parabola model equations. 
            
            Assuming that 1 unit in Unity represents 1 Meter in the real world
            we have that the gravity 9.8 m/s and the time, 
            due to the fact that we are extracting 25 FPS, 
            in this case is t/25 """

        t = t/25

        x = self.initial_x + self.v_x * t
        y = self.initial_y + self.v_y * t + 0.5 * self.g * (t ** 2)
        z = self.initial_z + self.v_z * t 

        out = np.asarray([x, y, z])
        return out

    def get_projection_matrix(self):
        """ The method returns the projection matrix """
        return self.proj_matrix

    def accuracy(self, out, labels):
        """ The method computes the RMSE between prediction and labels """
        rmse = np.sqrt(((out - labels) ** 2).mean())
        mse = ((out - labels) ** 2).mean()
        return rmse