import numpy as np

def install(m):
    def solve_qp_dynamic(final_std, states, xbar,
                         rho=None, beta=None, ridge_lambda=None, C=None):
        if rho is None: rho=m.SMOKE_RHO
        if beta is None: beta=m.SMOKE_BETA
        if ridge_lambda is None: ridge_lambda=m.SMOKE_LAMBDA
        if C is None: C=m.SMOKE_C
        errors=[]

        involved_states={x for pair in m.EQUALITY_PAIRS + m.ORDER_PAIRS for x in pair}
        for label in sorted(involved_states):
            if states[label]["U"] != 0:
                errors.append(f"{label}: U_A={states[label]['U']} but QP requires U_A=0.")

        Q_var,q_stats=m.assemble_qvar(states)
        if not q_stats["finite"]:
            errors.append("Q_var contains non-finite values.")
        if q_stats["symmetry_error"] > 1e-12:
            errors.append(f"Q_var symmetry error {q_stats['symmetry_error']} exceeds tolerance.")
        if q_stats["min_eigenvalue"] < -1e-8:
            errors.append(f"Q_var minimum eigenvalue {q_stats['min_eigenvalue']} < -1e-8.")
        if xbar is None or np.asarray(xbar).shape != (len(m.MODEL_FEATURES),):
            errors.append("Invalid xbar_PBS0 for QP.")

        living=final_std["status"].isin(["observed","imputed"])
        X_live=final_std.loc[living,m.MODEL_FEATURES].to_numpy(dtype=float)
        live_meta=final_std.loc[living,["mouse_id","group","week","status"]].copy()
        if len(X_live)==0:
            errors.append("No living complete rows available for positivity constraints.")
        if not np.isfinite(X_live).all():
            errors.append("Non-finite values in positivity design matrix.")
        if errors:
            return None,{"status":"NOT_SOLVED","errors":errors,"qvar":q_stats}

        p=len(m.MODEL_FEATURES)
        n_order=len(m.ORDER_PAIRS)
        w=m.cp.Variable(p,name="w")
        eta=m.cp.Variable(n_order,nonneg=True,name="eta")
        objective_terms=[
            m.cp.quad_form(w,m.cp.psd_wrap(Q_var)),
            ridge_lambda*m.cp.sum_squares(w),
            C*m.cp.sum(eta),
        ]

        equality_exprs=[]
        for A,B in m.EQUALITY_PAIRS:
            c_ab,d_ab=m.pair_affine_components(states,A,B)
            equality_exprs.append(c_ab+d_ab@w)
        objective_terms.append(beta*m.cp.sum_squares(m.cp.hstack(equality_exprs)))

        constraints=[]
        for k,(A,B) in enumerate(m.ORDER_PAIRS):
            c_ab,d_ab=m.pair_affine_components(states,A,B)
            expr=c_ab+d_ab@w
            constraints.append(expr >= rho-eta[k])

        centered_live=X_live-np.asarray(xbar,dtype=float)
        constraints.append(1.0+centered_live@w >= m.POSITIVITY_EPSILON)

        problem=m.cp.Problem(m.cp.Minimize(sum(objective_terms)),constraints)
        try:
            objective_value=problem.solve(
                solver=m.cp.OSQP,eps_abs=1e-8,eps_rel=1e-8,max_iter=100000,verbose=False
            )
        except Exception as exc:
            return None,{"status":"SOLVER_EXCEPTION","errors":[f"OSQP exception: {type(exc).__name__}: {exc}"],"qvar":q_stats}

        solver_status=str(problem.status)
        if solver_status not in {m.cp.OPTIMAL,m.cp.OPTIMAL_INACCURATE}:
            errors.append(f"Unexpected solver status: {solver_status}.")
        if w.value is None or eta.value is None:
            errors.append("Solver returned no primal solution.")
            return None,{"status":solver_status,"errors":errors,"qvar":q_stats,
                         "objective":None if objective_value is None else float(objective_value)}

        wv=np.asarray(w.value,dtype=float).reshape(-1)
        etav=np.asarray(eta.value,dtype=float).reshape(-1)

        equality_deltas={}
        for A,B in m.EQUALITY_PAIRS:
            c_ab,d_ab=m.pair_affine_components(states,A,B)
            equality_deltas[f"{A}>{B}"]=float(c_ab+d_ab@wv)

        order_results={}
        max_order_violation=0.0
        min_order_residual=float("inf")
        for k,(A,B) in enumerate(m.ORDER_PAIRS):
            c_ab,d_ab=m.pair_affine_components(states,A,B)
            delta=float(c_ab+d_ab@wv)
            residual=float(delta-rho+etav[k])
            violation=max(0.0,-residual)
            max_order_violation=max(max_order_violation,violation)
            min_order_residual=min(min_order_residual,residual)
            order_results[f"{A}>{B}"]={
                "delta":delta,"slack":float(etav[k]),"residual":residual,"violation":violation
            }

        eta_nonneg_violation=max(0.0,float(-np.min(etav))) if len(etav) else 0.0
        live_enri=1.0+centered_live@wv
        min_live_enri=float(np.min(live_enri))
        positivity_residuals=live_enri-m.POSITIVITY_EPSILON
        min_positivity_residual=float(np.min(positivity_residuals))
        max_positivity_violation=max(0.0,-min_positivity_residual)
        min_idx=int(np.argmin(live_enri))
        min_meta=live_meta.iloc[min_idx].to_dict()
        min_meta["week"]=int(min_meta["week"])

        group_means={label:float(state["a"]+state["b"]@wv) for label,state in states.items()}
        pbs0_normalization_error=abs(group_means["PBS^0"]-1.0)

        variance_term=float(wv@Q_var@wv)
        equality_term=float(beta*sum(v*v for v in equality_deltas.values()))
        ridge_term=float(ridge_lambda*(wv@wv))
        slack_term=float(C*np.sum(etav))
        objective_recomputed=variance_term+equality_term+ridge_term+slack_term
        objective_solver=float(problem.value)
        objective_gap=abs(objective_recomputed-objective_solver)

        if max_order_violation > m.QP_TOLERANCE:
            errors.append(f"Maximum order-constraint violation {max_order_violation} > {m.QP_TOLERANCE}.")
        if eta_nonneg_violation > m.QP_TOLERANCE:
            errors.append(f"Slack nonnegativity violation {eta_nonneg_violation} > {m.QP_TOLERANCE}.")
        if max_positivity_violation > m.QP_TOLERANCE:
            errors.append(f"Maximum positivity violation {max_positivity_violation} > {m.QP_TOLERANCE}.")
        if pbs0_normalization_error > m.QP_TOLERANCE:
            errors.append(f"PBS^0 normalization error {pbs0_normalization_error} > {m.QP_TOLERANCE}.")
        if objective_gap > 1e-6*max(1.0,abs(objective_solver)):
            errors.append(f"Recomputed objective differs from solver objective by {objective_gap}.")

        stats=problem.solver_stats
        result={
            "w":wv,"eta":etav,"qvar":Q_var,"qvar_stats":q_stats,
            "solver_status":solver_status,"solver_name":str(stats.solver_name),
            "solver_num_iters":None if stats.num_iters is None else int(stats.num_iters),
            "solver_time":None if stats.solve_time is None else float(stats.solve_time),
            "objective":objective_solver,
            "objective_components":{
                "variance":variance_term,"equality":equality_term,"ridge":ridge_term,"slack":slack_term
            },
            "objective_recomputed":objective_recomputed,"objective_gap":objective_gap,
            "equality_deltas":equality_deltas,"order_results":order_results,
            "group_means":group_means,"min_live_enri":min_live_enri,
            "min_live_enri_meta":min_meta,"min_positivity_residual":min_positivity_residual,
            "max_positivity_violation":max_positivity_violation,
            "max_order_violation":max_order_violation,"min_order_residual":min_order_residual,
            "eta_nonneg_violation":eta_nonneg_violation,
            "pbs0_normalization_error":pbs0_normalization_error,
            "weight_l2_norm":float(np.linalg.norm(wv)),
            "weight_max_abs":float(np.max(np.abs(wv))),
            "slack_sum":float(np.sum(etav)),
            "slack_max":float(np.max(etav)) if len(etav) else 0.0,
            "errors":errors,
        }
        return result,{"status":solver_status,"errors":errors,"qvar":q_stats}

    m.solve_qp_smoke=solve_qp_dynamic
    return m
