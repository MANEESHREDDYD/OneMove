from onemove_intelligence.ml.dispatch_optimizer import optimize_dispatch

def test_optimize_dispatch():
    matrix = optimize_dispatch()
    assert matrix.shape == (5, 5)
    assert (matrix >= 0).all()
