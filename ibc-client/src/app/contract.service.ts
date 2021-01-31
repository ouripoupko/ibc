import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';

import { Observable, of } from 'rxjs';
import { catchError, map, tap } from 'rxjs/operators';

import { Contract } from './contract';
import { CONTRACTS } from './mock-contracts';
import { MessageService } from './message.service';

@Injectable({
  providedIn: 'root'
})
export class ContractService {

  private contractUrl = 'contract';
  httpOptions = {
    headers: new HttpHeaders({ 'Content-Type': 'application/json' })
  };

  constructor(
    private http: HttpClient,
    private messageService: MessageService) { }

  private log(message: string) {
    this.messageService.add(`contractService: ${message}`);
  }

  /** GET **/
  getContracts(): Observable<Contract[]> {
    return this.http.get<Contract[]>(this.contractUrl)
      .pipe(
        tap(_ => this.log('fetched contracts')),
        catchError(this.handleError<Contract[]>('getContracts', []))
      );
  }

  /** GET **/
  getContract(name: string): Observable<Contract> {
    const url = `${this.contractUrl}/${name}`;
    return this.http.get<Contract>(url).pipe(
      tap(_ => this.log(`fetched contract name=${name}`)),
      catchError(this.handleError<Contract>(`getContract name=${name}`))
    );
  }

  /** PUT **/
  updateContract(name: string, contract: Contract): Observable<any> {
    const url = `${this.contractUrl}/${name}`;
    return this.http.put(url, contract, this.httpOptions).pipe(
      tap(_ => this.log(`updated contract name=${contract.name}`)),
      catchError(this.handleError<any>('updateContract'))
    );
  }

  /** POST **/
  addContract(contract: Contract): Observable<Contract> {
    return this.http.post<Contract>(this.contractUrl, contract, this.httpOptions).pipe(
      tap((newContract: Contract) => this.log(`added contract with name=${newContract.name}`)),
      catchError(this.handleError<Contract>('addContract'))
    );
  }

  /**
   * Handle Http operation that failed.
   * Let the app continue.
   * @param operation - name of the operation that failed
   * @param result - optional value to return as the observable result
  */
  private handleError<T>(operation = 'operation', result?: T) {
    return (error: any): Observable<T> => {

      // TODO: send the error to remote logging infrastructure
      console.error(error); // log to console instead

      // TODO: better job of transforming error for user consumption
      this.log(`${operation} failed: ${error.message}`);

      // Let the app keep running by returning an empty result.
      return of(result as T);
    };
  }
}
