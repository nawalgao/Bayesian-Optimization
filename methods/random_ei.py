from .bo import BO
import numpy as np
import scipy as sp


class Random_EI(BO):
    '''
    Naive batch strategy where the first point is the minimizer of the
    one-point expected improvement and the rest are chosen uniformly at random
    '''
    def __init__(self, options):
        super(Random_EI, self).__init__(options)

    @classmethod
    def acquisition_fun(cls, X, m):
        '''
        This is simply the EI acqusition function. Code is taken from GPyOpt.
        '''
        ############################################################
        # Copied from GPyOpt/models/gpmodel/predict_withGradients
        # (changed to predict_noiseless)
        ############################################################
        mu, v = m.predict_noiseless(X)
        v = np.clip(v, 1e-10, np.inf)
        s = np.sqrt(v)

        dmudx, dvdx = m.predictive_gradients(X)
        dmudx = dmudx[:, :, 0]
        dsdx = dvdx / (2*np.sqrt(v))
        ###############

        ############################################################
        # Copied from GPyOpt/acqusitions/EI/_compute_acq_withGradients
        ############################################################
        fmin = np.min(m.Y)

        u = (fmin-mu)/s
        phi = np.exp(-0.5 * u**2) / np.sqrt(2*np.pi)
        Phi = 0.5 * sp.special.erfc(-u / np.sqrt(2))

        opt_val = -(fmin - mu) * Phi - s * phi
        dpdX = -dsdx * phi + Phi * dmudx

        return opt_val, dpdX

    @classmethod
    def acquisition_fun_flat(cls, X, m):
        '''
        Wrapper for acquisition_fun, where X is considered as a vector
        '''
        n = m.X.shape[1]
        k = X.shape[0]//n

        (opt_val, dpdX) = cls.acquisition_fun(X.reshape(k, n), m)
        return opt_val, dpdX.flatten()

    def acq_fun_optimizer(self, m):
        # X will hold the final choice of the 1st point in the batch
        X = None
        # Y will hold the EI of X
        y = None

        # Run local gradient-descent optimizer multiple times
        # to avoid getting stuck in a poor local optimum
        for j in range(self.acq_opt_restarts):
            X0 = self.random_sample(self.bounds, 1)
            try:
                res = sp.optimize.minimize(fun=self.acquisition_fun_flat,
                                           x0=X0.flatten(),
                                           args=(m),
                                           method='L-BFGS-B',
                                           jac=True,
                                           bounds=self.bounds,
                                           options=self.optimizer_options)

                '''
                self.derivative_check(
                    lambda X: self.acquisition_fun_flat(X, m), 1
                    )
                '''

                X0 = res.x.reshape(1, self.dim)
                y0 = res.fun[0]

                # Update X if the current local minimum is
                # the best one found so far
                if X is None or y0 < y:
                    X = X0
                    y = y0
            except:
                print('Optimization failed')

        # Fill the rest of the batch with points selected uniformly at random
        X_random = self.random_sample(self.bounds, self.batch_size - 1)
        X_final = np.concatenate((X, X_random))

        return X_final
