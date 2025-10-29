import tenseal as ts
import numpy as np
from fediux.utils.logger_util import logger


class KmeansBase:
    def __init__(self, n_clusters=3, max_iter=100, tol=1e-4):
        self.n_clusters = n_clusters
        self.max_iter = max_iter
        self.tol = tol
        self.centers = None
        self.labels = None

    def _init_centers(self, x):
        raise NotImplementedError

    def _compute_distances(self, x):
        raise NotImplementedError

    def _assign_labels(self, distances):
        raise NotImplementedError

    def _update_centers(self, x, labels):
        raise NotImplementedError

    def fit(self, x):
        raise NotImplementedError


class KmeansHost_Plaintext(KmeansBase):
    def __init__(self, n_clusters=3, max_iter=100, tol=1e-4):
        super().__init__(n_clusters, max_iter, tol)
        self.partial_sums = None
        self.counts = None

    def _init_centers(self, x):
        self.centers = x[np.random.choice(x.shape[0], self.n_clusters, replace=False)]
        
    def _compute_distances(self, x):
        return np.array([np.sum((x - center)**2, axis=1) for center in self.centers]).T
    
    def _assign_labels(self, distances):
        return np.argmin(distances, axis=1)
    
    def _update_centers(self, x, labels):
        new_centers = np.zeros_like(self.centers)
        for i in range(self.n_clusters):
            mask = (labels == i)
            if np.sum(mask) > 0:
                new_centers[i] = x[mask].mean(axis=0)
        return new_centers


class KmeansGuest_Plaintext(KmeansBase):
    def __init__(self, n_clusters=3, max_iter=100, tol=1e-4):
        super().__init__(n_clusters, max_iter, tol)
        self.centers = None

    def _init_centers(self, x):
        self.centers = x[np.random.choice(x.shape[0], self.n_clusters, replace=False)]
        
    def _compute_distances(self, x):
        if self.centers is None:
            raise ValueError("Centers not initialized")
        return np.array([np.sum((x - center)**2, axis=1) for center in self.centers]).T
    
    def _update_centers(self, x, labels):
        new_centers = np.zeros_like(self.centers)
        for i in range(self.n_clusters):
            mask = (labels == i)
            if np.sum(mask) > 0:
                new_centers[i] = x[mask].mean(axis=0)
        return new_centers

